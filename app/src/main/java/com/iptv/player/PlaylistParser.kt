package com.iptv.player

import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.BufferedReader
import java.io.StringReader
import java.util.concurrent.TimeUnit

object PlaylistParser {
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    suspend fun fetchPlaylist(url: String): List<Channel> {
        val request = Request.Builder().url(url).build()
        val response = client.newCall(request).execute()
        if (!response.isSuccessful) throw Exception("HTTP ${response.code}")
        val content = response.body?.string() ?: throw Exception("Empty body")
        return parse(content, url)
    }

    private fun parse(content: String, url: String): List<Channel> {
        return if (url.endsWith(".m3u") || url.endsWith(".m3u8")) {
            parseM3u(content)
        } else {
            parseTxt(content)
        }
    }

    private fun parseM3u(content: String): List<Channel> {
        val channels = mutableListOf<Channel>()
        val lines = content.lines()
        var currentName = ""
        for (line in lines) {
            if (line.startsWith("#EXTINF")) {
                val match = Regex(",(.+)$").find(line)
                currentName = match?.groupValues?.get(1)?.trim() ?: ""
            } else if (line.trim().startsWith("http")) {
                if (currentName.isNotBlank()) {
                    channels.add(Channel(currentName, line.trim()))
                    currentName = ""
                }
            }
        }
        return channels
    }

    private fun parseTxt(content: String): List<Channel> {
        val channels = mutableListOf<Channel>()
        var currentName = ""
        content.lines().forEach { line ->
            val trimmed = line.trim()
            when {
                trimmed.startsWith("#") && !trimmed.startsWith("#EXT") -> {
                    currentName = trimmed.removePrefix("#").trim()
                }
                trimmed.startsWith("http") -> {
                    val name = if (currentName.isBlank()) "频道" else currentName
                    channels.add(Channel(name, trimmed))
                    currentName = ""
                }
            }
        }
        return channels
    }
}
