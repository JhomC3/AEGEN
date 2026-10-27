package com.jhomc.healthsync

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SyncExecutorTest {

    @Test
    fun `reportJson respeta el contrato sync-report`() {
        val json = SyncExecutor.reportJson(
            typesSynced = 29,
            delivered = 633,
            failed = 0,
            quarantined = 3072,
            quarantineSample = "record_type fuera de allow-list",
            quarantineByType = mapOf("HEART_RATE_VARIABILITY_RMSSD" to 3072),
            notice = null,
            permanentError = null,
            nutritionPublished = 3,
            nutritionFailed = 0,
            deviceId = "android-test",
        )
        assertEquals(1, json.getInt("schema_version"))
        assertEquals("android-test", json.getString("device_id"))
        assertEquals(29, json.getInt("types_synced"))
        assertEquals(633, json.getInt("delivered"))
        assertEquals(3072, json.getInt("quarantined"))
        assertEquals(
            3072,
            json.getJSONObject("quarantine_by_type").getInt("HEART_RATE_VARIABILITY_RMSSD"),
        )
        assertTrue(json.isNull("notice"))
        assertTrue(json.isNull("permanent_error"))
        assertEquals(3, json.getInt("nutrition_published"))
    }
}
