package com.iptv.player

import android.content.Context
import android.util.Log
import com.iptv.player.model.Channel
import com.iptv.player.model.ChannelGroup
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

object DataManager {
    private const val TAG = "DataManager"
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    var allChannels: List<Channel> = emptyList()
    var channelGroups: List<ChannelGroup> = emptyList()

    suspend fun loadChannels(context: Context): Boolean = withContext(Dispatchers.IO) {
        try {
            val txtUrl = BuildConfig.IPTV_TXT_URL
            val request = Request.Builder().url(txtUrl).build()
            val response = client.newCall(request).execute()

            if (!response.isSuccessful) {
                Log.e(TAG, "HTTP error: ${response.code}")
                return@withContext false
            }

            val content = response.body?.string() ?: return@withContext false
            val channels = parseTxtContent(content)

            if (channels.isEmpty()) {
                Log.e(TAG, "Parsed 0 channels")
                return@withContext false
            }

            allChannels = channels
            channelGroups = groupChannels(channels)

            Log.i(TAG, "Loaded ${channels.size} channels, ${channelGroups.size} groups")
            return@withContext true
        } catch (e: Exception) {
            Log.e(TAG, "Error loading channels", e)
            return@withContext false
        }
    }

    private fun parseTxtContent(content: String): List<Channel> {
        val channels = mutableListOf<Channel>()
        var currentGroup = ""
        content.lines().forEach { line ->
            val trimmed = line.trim()
            when {
                trimmed.startsWith("#") && !trimmed.startsWith("#EXT") -> {
                    currentGroup = trimmed.drop(1).trim()
                }
                trimmed.contains(",") && trimmed.contains("http") -> {
                    val lastComma = trimmed.lastIndexOf(',')
                    if (lastComma > 0 && lastComma < trimmed.length - 1) {
                        val name = trimmed.substring(0, lastComma).trim()
                        val url = trimmed.substring(lastComma + 1).trim()
                        if (url.startsWith("http")) {
                            channels.add(Channel(name, url, currentGroup))
                        }
                    }
                }
                trimmed.startsWith("http") -> {
                    val url = trimmed
                    val name = "频道${channels.size + 1}"
                    channels.add(Channel(name, url, currentGroup))
                }
            }
        }
        return channels
    }

    private fun groupChannels(channels: List<Channel>): List<ChannelGroup> {
        val groupMap = mutableMapOf<String, MutableList<Channel>>()
        channels.forEach { channel ->
            val groupName = channel.group.ifEmpty { "其他" }
            groupMap.getOrPut(groupName) { mutableListOf() }.add(channel)
        }

        val order = listOf("央视", "卫视", "地方", "港澳台", "📺央视频道", "📡卫视频道",
            "☘️北京频道", "☘️上海频道", "☘️天津频道", "☘️重庆频道", "☘️广东频道",
            "☘️浙江频道", "☘️江苏频道", "其他")

        return groupMap.entries
            .sortedBy { (key, _) ->
                order.indexOfFirst { key.contains(it) }.let { if (it == -1) order.size else it }
            }
            .map { ChannelGroup(it.key, it.value) }
    }
}
