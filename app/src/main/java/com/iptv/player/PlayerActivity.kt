package com.iptv.player

import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.google.android.exoplayer2.ExoPlayer
import com.google.android.exoplayer2.MediaItem
import com.google.android.exoplayer2.PlaybackException
import com.google.android.exoplayer2.Player
import com.google.android.exoplayer2.source.hls.HlsMediaSource
import com.google.android.exoplayer2.ui.PlayerView
import com.google.android.exoplayer2.upstream.DefaultHttpDataSource

class PlayerActivity : AppCompatActivity() {
    private lateinit var playerView: PlayerView
    private lateinit var progressBar: ProgressBar
    private lateinit var errorText: TextView
    private var exoPlayer: ExoPlayer? = null
    private var currentUrl: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_player)

        playerView = findViewById(R.id.playerView)
        progressBar = findViewById(R.id.progressBar)
        errorText = findViewById(R.id.errorText)

        val channelName = intent.getStringExtra("channel_name") ?: "未知频道"
        currentUrl = intent.getStringExtra("channel_url")

        supportActionBar?.title = channelName
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        if (currentUrl.isNullOrEmpty()) {
            showError("无效的播放地址")
        } else {
            initializePlayer()
        }
    }

    private fun initializePlayer() {
        exoPlayer = ExoPlayer.Builder(this).build().apply {
            val dataSourceFactory = DefaultHttpDataSource.Factory()
                .setAllowCrossProtocolRedirects(true)
                .setConnectTimeoutMs(10000)
                .setReadTimeoutMs(10000)

            val mediaSource = HlsMediaSource.Factory(dataSourceFactory)
                .createMediaSource(MediaItem.fromUri(Uri.parse(currentUrl)))

            setMediaSource(mediaSource)
            prepare()
            playWhenReady = true

            addListener(object : Player.Listener {
                override fun onPlaybackStateChanged(playbackState: Int) {
                    when (playbackState) {
                        ExoPlayer.STATE_BUFFERING -> {
                            progressBar.visibility = View.VISIBLE
                            errorText.visibility = View.GONE
                        }
                        ExoPlayer.STATE_READY -> {
                            progressBar.visibility = View.GONE
                        }
                        ExoPlayer.STATE_ENDED -> {
                            finish()
                        }
                    }
                }

                override fun onPlayerError(error: PlaybackException) {
                    showError("播放失败: ${error.message}")
                }
            })

            playerView.player = this
        }
    }

    private fun showError(msg: String) {
        progressBar.visibility = View.GONE
        errorText.visibility = View.VISIBLE
        errorText.text = msg
        playerView.visibility = View.GONE
    }

    override fun onStart() {
        super.onStart()
        exoPlayer?.playWhenReady = true
    }

    override fun onStop() {
        super.onStop()
        exoPlayer?.playWhenReady = false
    }

    override fun onDestroy() {
        super.onDestroy()
        exoPlayer?.release()
        exoPlayer = null
    }

    override fun onSupportNavigateUp(): Boolean {
        onBackPressedDispatcher.onBackPressed()
        return true
    }
}
