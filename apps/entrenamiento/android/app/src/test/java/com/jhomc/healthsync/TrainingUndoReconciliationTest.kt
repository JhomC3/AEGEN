package com.jhomc.healthsync

import android.app.Application
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import com.jhomc.healthsync.data.HealthDatabase
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import java.time.LocalDate
import java.util.concurrent.TimeUnit

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class TrainingUndoReconciliationTest {
    private lateinit var db: HealthDatabase
    private lateinit var server: MockWebServer
    private lateinit var repo: TrainingRepository
    private lateinit var vm: TrainingDiaryViewModel
    private val fecha = LocalDate.now().toString()
    private val draft = TrainingSetDraft("Press", "14", "11", "2.3", "")
    private val savedSets = """[{"set_orden":1,"ejercicio":"Press","kg":14,"reps":11,"rir":2.3,"descanso_seg":null,"rm":20.2}]"""

    @Before fun setUp() {
        val app = ApplicationProvider.getApplicationContext<Application>()
        db = Room.inMemoryDatabaseBuilder(app, HealthDatabase::class.java).build()
        repo = TrainingRepository(db.trainingCacheDao(), db.offlineDao())
        server = MockWebServer().also { it.start() }
        vm = TrainingDiaryViewModel(app, false, repo)
        vm.draftsDaoOverride = db.entrenoDraftDao()
    }

    @After fun tearDown() {
        server.shutdown()
        db.close()
    }

    private val base get() = server.url("/").toString().trimEnd('/')

    private fun reply(sets: String) {
        server.enqueue(MockResponse().setBody(
            """{"schema_version":1,"fecha":"$fecha","semana":22,"dia":"SABADO","has_data":${sets != "[]"},"sets":$sets}""",
        ))
    }

    private suspend fun cacheSavedSession() {
        reply(savedSets)
        assertNull(repo.loadSession(base, "test-token", fecha).error)
        vm.draftBuffer = fecha to listOf(draft)
        assertNull(db.entrenoDraftDao().forFecha(fecha))
    }

    @Test fun `undo remoto invalida memoria sin fila local y no reenvia`() = runBlocking {
        cacheSavedSession()
        repo.enqueueSessionSave(fecha, listOf(draft))
        reply("[]")
        val result = vm.reconcileDay(base, "test-token", fecha)
        assertTrue(result.replaced)
        assertNull(vm.draftBuffer)
        assertEquals(0, repo.pendingCount())
        assertEquals(0, repo.drainOutbox(base, "test-token"))
        assertEquals(2, server.requestCount)
        repeat(2) { assertEquals("GET", server.takeRequest(1, TimeUnit.SECONDS)?.method) }
    }

    @Test fun `servidor sin cambios conserva edicion local`() = runBlocking {
        cacheSavedSession()
        vm.draftBuffer = fecha to listOf(draft.copy(kg = "15"))
        reply(savedSets)
        assertFalse(vm.reconcileDay(base, "test-token", fecha).replaced)
        assertEquals("15", vm.draftBuffer!!.second.single().kg)
    }

    @Test fun `lectura 429 conserva memoria y cola sin POST`() = runBlocking {
        cacheSavedSession()
        repo.enqueueSessionSave(fecha, listOf(draft))
        server.enqueue(MockResponse().setResponseCode(429).setBody("limite"))
        assertFalse(vm.reconcileDay(base, "test-token", fecha).replaced)
        assertNotNull(vm.draftBuffer)
        assertEquals(1, repo.pendingCount())
        repeat(2) { assertEquals("GET", server.takeRequest(1, TimeUnit.SECONDS)?.method) }
    }
}
