package com.jhomc.healthsync

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SpeedAvgBucketizerTest {

    private val h = SpeedAvgBucketizer.HOUR_MS

    @Test
    fun `empty input yields no buckets`() {
        assertTrue(SpeedAvgBucketizer.bucketize(emptyList()).isEmpty())
    }

    @Test
    fun `samples in the same hour average without idle dilution`() {
        // Solo se emite la hora con muestras: el tiempo quieto no existe aquí.
        val buckets = SpeedAvgBucketizer.bucketize(
            listOf((2 * h + 100) to 2.0, (2 * h + 2000) to 4.0),
        )
        assertEquals(1, buckets.size)
        assertEquals(2 * h, buckets[0].startEpochMs)
        assertEquals(3 * h, buckets[0].endEpochMs)
        assertEquals(3.0, buckets[0].avgMps, 1e-9)
        assertEquals(4.0, buckets[0].maxMps, 1e-9)
        assertEquals(2, buckets[0].sampleCount)
    }

    @Test
    fun `hour boundary splits buckets and output is sorted`() {
        val buckets = SpeedAvgBucketizer.bucketize(
            listOf((5 * h + 10) to 1.0, (3 * h + h - 1) to 2.0, (3 * h) to 4.0),
        )
        assertEquals(listOf(3 * h, 5 * h), buckets.map { it.startEpochMs })
        assertEquals(3.0, buckets[0].avgMps, 1e-9)
        assertEquals(4.0, buckets[0].maxMps, 1e-9)
        assertEquals(2, buckets[0].sampleCount)
    }

    @Test
    fun `invalid samples are skipped`() {
        val buckets = SpeedAvgBucketizer.bucketize(
            listOf((h + 1) to Double.NaN, (h + 2) to -1.0, (h + 3) to 3.0),
        )
        assertEquals(1, buckets.size)
        assertEquals(3.0, buckets[0].avgMps, 1e-9)
        assertEquals(1, buckets[0].sampleCount)
    }

    @Test
    fun `hc ids are stable per hour and entity is tiny`() {
        assertEquals("SPD_H1:7200000", SpeedAvgBucketizer.hcId(2 * h))
        val entity = SpeedAvgBucketizer.toEntity(
            SpeedHourBucket(2 * h, 3 * h, 3.0, 4.0, 2), nowMs = 9L,
        )
        assertEquals("SPD_H1:7200000", entity.hcId)
        assertEquals("SPEED_H1", entity.recordType)
        assertEquals(2 * h, entity.startEpochMs)
        assertEquals(3 * h, entity.endEpochMs)
        assertEquals("""{"avg_mps":3.0,"max_mps":4.0,"n":2}""", entity.valueJson)
        assertTrue("agregado liviano", entity.valueJson.length < 100)
    }
}
