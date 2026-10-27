package com.jhomc.healthsync

import com.jhomc.healthsync.data.HealthRecordEntity

/** Un tramo de 1 hora: promedio/máx/n de las muestras que caen dentro. */
data class SpeedHourBucket(
    val startEpochMs: Long,
    val endEpochMs: Long,
    val avgMps: Double,
    val maxMps: Double,
    val sampleCount: Int,
)

/**
 * Agrupa muestras crudas de velocidad en promedios por hora (SPEED_H1).
 * Puro y determinista (por epoch, sin zona horaria): cada muestra imputa a
 * la hora de su inicio. Solo se emiten horas CON al menos una muestra, así
 * que el tiempo quieto (sin muestras) no tira el promedio a cero: es el
 * promedio en movimiento, no del reloj. Espejo del precedente
 * HourlySumBucketizer (suma) y HrBucketizer (tramos de 5 min).
 *
 * Corte hacia adelante: el crudo SPEED deja de subirse y este agregado
 * arranca con historial corto (4 días); el servidor conserva el histórico
 * crudo. La velocidad no se visualiza en el dashboard: el agregado solo
 * ahorra volumen (~24 filas/día de ~60 bytes frente a ~50 crudos/día de
 * 1–3 KB).
 */
object SpeedAvgBucketizer {

    const val RECORD_TYPE = "SPEED_H1"
    const val HOUR_MS = 3_600_000L

    fun bucketize(
        samples: List<Pair<Long, Double>>,
        hourMs: Long = HOUR_MS,
    ): List<SpeedHourBucket> {
        if (samples.isEmpty()) return emptyList()
        val buckets = LinkedHashMap<Long, MutableList<Double>>()
        for ((timeMs, mps) in samples) {
            if (mps.isNaN() || mps.isInfinite() || mps < 0) continue
            val hour = timeMs / hourMs * hourMs
            buckets.getOrPut(hour) { mutableListOf() }.add(mps)
        }
        return buckets.map { (hour, values) ->
            SpeedHourBucket(
                startEpochMs = hour,
                endEpochMs = hour + hourMs,
                avgMps = values.average(),
                maxMps = values.max(),
                sampleCount = values.size,
            )
        }.sortedBy { it.startEpochMs }
    }

    /** hc_id estable por tramo: idempotente entre syncs (re-agregar = overwrite). */
    fun hcId(startEpochMs: Long): String = "SPD_H1:$startEpochMs"

    fun toEntity(bucket: SpeedHourBucket, nowMs: Long): HealthRecordEntity =
        HealthRecordEntity(
            hcId = hcId(bucket.startEpochMs),
            recordType = RECORD_TYPE,
            startEpochMs = bucket.startEpochMs,
            endEpochMs = bucket.endEpochMs,
            lastModifiedEpochMs = bucket.startEpochMs,
            dataOriginPackage = null, // una hora puede mezclar proveedores
            timeZoneOffsetMinutes = null,
            payloadSchemaVersion = 1,
            valueJson = """{"avg_mps":${bucket.avgMps},"max_mps":${bucket.maxMps},"n":${bucket.sampleCount}}""",
            sourceUpdatedAtEpochMs = nowMs,
        )
}
