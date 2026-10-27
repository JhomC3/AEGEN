package com.jhomc.healthsync

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

/** Etapas del sync observables desde la UI (panel) y la notificación. */
sealed interface SyncStage {
    data object Idle : SyncStage
    data class Running(val stage: String) : SyncStage
    data class Done(val report: SyncReport) : SyncStage
    data class Failed(val error: String) : SyncStage
}

/**
 * Ejecuta la sincronización en un servicio en primer plano: Android trata la
 * app como activa aunque la pantalla esté apagada, y Health Connect sigue
 * aceptando las lecturas (su recomendación oficial para lecturas largas).
 * El progreso vive en [progress] (StateFlow) y se refleja en la notificación.
 */
class SyncService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var watchdog: Job? = null

    override fun onCreate() {
        super.onCreate()
        createChannel(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForegroundCompat("Iniciando sincronización…")
        progress.value = SyncStage.Running("Iniciando…")

        // Watchdog: si el sync se cuelga, el servicio termina con error claro.
        watchdog = scope.launch {
            delay(WATCHDOG_MS)
            if (progress.value is SyncStage.Running) {
                progress.value = SyncStage.Failed(
                    "Timeout: la sincronización no terminó en ${WATCHDOG_MS / 60_000} min",
                )
                stopSelf()
            }
        }

        scope.launch {
            try {
                val report = runner(this@SyncService) { stage ->
                    progress.value = SyncStage.Running(stage)
                    notify("Sincronizando…")
                }
                progress.value = SyncStage.Done(report)
                notify("Sincronizado.")
            } catch (e: kotlinx.coroutines.CancellationException) {
                // El sistema detuvo el servicio (MIUI es agresivo con el fondo):
                // el checkpoint en Room conserva el progreso; se reanuda solo.
                val text = "Sincronización interrumpida por el sistema; " +
                    "se reanudará donde quedó (los datos ya leídos están a salvo)."
                progress.value = SyncStage.Failed(text)
                notify("No se pudo sincronizar.")
            } catch (e: Exception) {
                progress.value = SyncStage.Failed(e.message ?: e.javaClass.simpleName)
                notify("No se pudo sincronizar.")
            } finally {
                watchdog?.cancel()
                getSystemService(NotificationManager::class.java).cancel(NOTIFICATION_ID)
                stopSelf()
            }
        }
        // START_NOT_STICKY: si el sistema mata el servicio, NO se relanza solo
        // (un relanzamiento automático volvía a mostrar la notificación zombi).
        // La reanudación la hace el usuario con el botón; el checkpoint en
        // Room conserva el progreso.
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun startForegroundCompat(text: String) {
        val notification = buildNotification(this, text)
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun notify(text: String) {
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(NOTIFICATION_ID, buildNotification(this, text))
    }

    companion object {
        const val CHANNEL_ID = "health_sync_progress"
        const val NOTIFICATION_ID = 1

        /**
         * Tope de seguridad por pulsación: si el sync se alarga (proveedor
         * lento, datos enormes), el servicio se detiene solo y el checkpoint
         * permite continuar en la siguiente pulsación.
         */
        const val WATCHDOG_MS = 15 * 60 * 1000L

        /** runner inyectable en tests; firma idéntica a SyncExecutor.run. */
        @Volatile
        var runner: suspend (Context, (String) -> Unit) -> SyncReport = { ctx, onProgress ->
            SyncExecutor.run(ctx, onProgress, force = true)
        }

        /** Progreso observable: la UI lo colecta para el panel. */
        val progress: MutableStateFlow<SyncStage> = MutableStateFlow(SyncStage.Idle)

        /** Arranca el servicio si no hay ya un sync en marcha. */
        fun start(context: Context) {
            if (progress.value is SyncStage.Running) return
            context.startForegroundService(Intent(context, SyncService::class.java))
        }

        fun createChannel(context: Context) {
            val manager = context.getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "Progreso de sincronización", NotificationManager.IMPORTANCE_LOW),
            )
        }

        fun buildNotification(context: Context, text: String): Notification {
            val intent = Intent(context, MainActivity::class.java)
            val pending = android.app.PendingIntent.getActivity(
                context,
                0,
                intent,
                android.app.PendingIntent.FLAG_UPDATE_CURRENT or android.app.PendingIntent.FLAG_IMMUTABLE,
            )
            return NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.stat_notify_sync)
                .setContentTitle("HealthSync")
                .setContentText(text)
                .setContentIntent(pending)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .build()
        }

        fun summaryOf(report: SyncReport): String = buildString {
            // Silencio nutricional por diseño: la publicación no se anuncia en
            // la UI (los contadores siguen en SyncReport/logs para diagnóstico).
            append("Tipos leídos: ${report.typesSynced} | Entregados: ${report.delivered}")
            if (report.failed > 0) append(" | Fallos: ${report.failed}")
            if (report.quarantined > 0) {
                append(" | Cuarentena: ${report.quarantined}")
                val detail = quarantineDetail(report)
                if (detail.isNotEmpty()) append(" ($detail)")
            }
            report.notice?.let { append(" | Aviso: $it") }
            report.permanentError?.let { append(" | Error: $it") }
        }

        /**
         * Detalle de cuarentena para el resumen: conteo por tipo (máx. 3, el
         * resto se resume) y, si no hay desglose, el primer motivo. Puro para
         * poder testearlo sin Activity.
         */
        fun quarantineDetail(report: SyncReport): String {
            if (report.quarantineByType.isNotEmpty()) {
                val top = report.quarantineByType.entries.sortedByDescending { it.value }.take(3)
                val shown = top.joinToString(", ") { "${shortType(it.key)}:${it.value}" }
                val rest = report.quarantineByType.size - top.size
                return if (rest > 0) "$shown (+$rest tipos)" else shown
            }
            return report.quarantineSample ?: ""
        }

        private fun shortType(type: String): String = type
            .removeSuffix("_RMSSD")
            .split("_")
            .mapNotNull { it.firstOrNull()?.toString() }
            .joinToString("")
            .take(4)

        /**
         * Frase corta para el aviso pequeño (Toast). null = todo bien (la UI
         * muestra "Sincronizado."). Sin números, URLs ni tecnicismos: el
         * detalle vive en el servidor (POST /sync/report). Función pura para
         * poder testearla sin Activity.
         */
        fun userMessage(report: SyncReport): String? {
            when (report.notice) {
                "rate_limited" -> return "Cuota agotada. Espera unos minutos e inténtalo de nuevo."
                "foreground_requerido" -> return "Concede el acceso en segundo plano en Health Connect."
                "timeout_lectura" -> return "Health Connect no respondió. Vuelve a intentarlo."
                "sin_destino" -> return "Sin destino. Instala el APK debug."
                "sin_token_guardado" -> return "Sin token. Reinstala el APK debug."
                "sin_permisos" -> return "Concede los permisos esenciales."
            }
            if (report.notice?.startsWith("url_invalida") == true) {
                return "Destino inválido. Recompila el APK."
            }
            if (report.permanentError?.contains("401") == true) {
                return "Token rechazado. Recompila el APK."
            }
            if (report.permanentError?.contains("400") == true) {
                return "Lote rechazado. Revisa el servidor."
            }
            return null
        }
    }
}
