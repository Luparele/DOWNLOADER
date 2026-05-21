package com.example.downloaderandroid

import android.app.Activity
import android.app.DownloadManager
import android.content.ContentValues
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.view.Gravity
import android.webkit.CookieManager
import android.webkit.URLUtil
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.net.URLDecoder

class MainActivity : Activity() {

    private lateinit var webView: WebView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Request storage permissions if needed (Android 9 or lower)
        checkStoragePermissions()

        // Create a stylish dark loading screen matching the UI theme
        val loadingLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setBackgroundColor(Color.parseColor("#0F172A")) // Slate 900
        }
        val spinner = ProgressBar(this).apply {
            isIndeterminate = true
        }
        val statusText = TextView(this).apply {
            text = "Inicializando interpretador Python..."
            setTextColor(Color.WHITE)
            textSize = 18f
            gravity = Gravity.CENTER
            setPadding(0, 40, 0, 0)
        }
        loadingLayout.addView(spinner)
        loadingLayout.addView(statusText)
        setContentView(loadingLayout)

        // Initialize WebView early
        webView = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.loadWithOverviewMode = true
            settings.useWideViewPort = true
            
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                    return false // Keep navigation inside the WebView
                }
            }

            setDownloadListener { url, userAgent, contentDisposition, mimetype, contentLength ->
                if (url.contains("/api/serve-file")) {
                    val uri = Uri.parse(url)
                    val filePath = uri.getQueryParameter("path")
                    if (filePath != null) {
                        Thread {
                            saveFileToPublicDownloads(filePath)
                        }.start()
                    }
                }
            }
        }

        // Start initialization and server thread
        Thread {
            try {
                // 1. (FFmpeg extraction removed - now bundled as native library)
                val ffmpegPath = applicationInfo.nativeLibraryDir + "/libffmpeg.so"

                // 2. Start Chaquopy
                runOnUiThread { statusText.text = "Iniciando interpretador..." }
                if (!Python.isStarted()) {
                    Python.start(AndroidPlatform(this))
                }

                // 3. Prepare Python module
                val py = Python.getInstance()
                // 4. Poll the server to check if it's already running
                runOnUiThread { statusText.text = "Conectando ao servidor local..." }
                var serverReady = false
                var attempts = 0
                
                // First check if server is already answering
                try {
                    val connection = java.net.URL("http://127.0.0.1:48921").openConnection() as java.net.HttpURLConnection
                    connection.connectTimeout = 1000
                    connection.readTimeout = 1000
                    connection.requestMethod = "GET"
                    if (connection.responseCode == 200) {
                        serverReady = true
                        android.util.Log.d("DownloaderAndroid", "Server already running on port 48921")
                    }
                } catch (e: Exception) {
                    android.util.Log.d("DownloaderAndroid", "Server not running yet, will start it.")
                }

                if (!serverReady) {
                    // Start FastAPI in the background
                    Thread {
                        try {
                            val runModule = py.getModule("run_app_android")
                            runModule.callAttr("start_server", filesDir.absolutePath, ffmpegPath)
                        } catch (e: Exception) {
                            e.printStackTrace()
                        }
                    }.start()

                    // Poll until it's ready
                    while (!serverReady && attempts < 30) {
                        attempts++
                        try {
                            val connection = java.net.URL("http://127.0.0.1:48921").openConnection() as java.net.HttpURLConnection
                            connection.connectTimeout = 2000
                            connection.readTimeout = 2000
                            connection.requestMethod = "GET"
                            val responseCode = connection.responseCode
                            android.util.Log.d("DownloaderAndroid", "Poll server response: $responseCode")
                            if (responseCode == 200) {
                                serverReady = true
                            } else {
                                Thread.sleep(1000)
                            }
                        } catch (e: Exception) {
                            android.util.Log.d("DownloaderAndroid", "Poll error on attempt $attempts: ${e.message}")
                            Thread.sleep(1000)
                        }
                    }
                }

                // 6. Load URL in WebView and display it
                runOnUiThread {
                    webView.loadUrl("http://127.0.0.1:48921")
                    setContentView(webView)
                }

            } catch (e: Exception) {
                e.printStackTrace()
                runOnUiThread {
                    statusText.text = "Erro na inicialização: ${e.message}"
                }
            }
        }.start()
    }


    private fun saveFileToPublicDownloads(filePath: String) {
        try {
            val decodedPath = URLDecoder.decode(filePath, "UTF-8")
            val sourceFile = File(filesDir, decodedPath)
            if (!sourceFile.exists()) {
                runOnUiThread {
                    Toast.makeText(this, "Arquivo não encontrado: ${sourceFile.name}", Toast.LENGTH_SHORT).show()
                }
                return
            }

            val fileName = sourceFile.name
            val resolver = contentResolver

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val contentValues = ContentValues().apply {
                    put(MediaStore.MediaColumns.DISPLAY_NAME, fileName)
                    put(MediaStore.MediaColumns.MIME_TYPE, getMimeType(fileName))
                    put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/Video Downloader")
                }
                val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, contentValues)
                if (uri != null) {
                    resolver.openOutputStream(uri).use { outputStream ->
                        FileInputStream(sourceFile).use { inputStream ->
                            inputStream.copyTo(outputStream!!)
                        }
                    }
                    sourceFile.delete() // <--- APAGA O RESÍDUO
                    runOnUiThread {
                        Toast.makeText(this, "Salvo em Downloads/Video Downloader: $fileName", Toast.LENGTH_LONG).show()
                    }
                } else {
                    throw Exception("Falha ao criar entrada no MediaStore")
                }
            } else {
                val baseDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
                val targetDir = File(baseDir, "Video Downloader")
                if (!targetDir.exists()) {
                    targetDir.mkdirs()
                }
                val targetFile = File(targetDir, fileName)
                FileInputStream(sourceFile).use { inputStream ->
                    FileOutputStream(targetFile).use { outputStream ->
                        inputStream.copyTo(outputStream)
                    }
                }
                sourceFile.delete() // <--- APAGA O RESÍDUO
                runOnUiThread {
                    Toast.makeText(this, "Salvo em Downloads/Video Downloader: $fileName", Toast.LENGTH_LONG).show()
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
            runOnUiThread {
                Toast.makeText(this, "Erro ao salvar arquivo: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    private fun getMimeType(fileName: String): String {
        return when {
            fileName.endsWith(".mp4", ignoreCase = true) -> "video/mp4"
            fileName.endsWith(".mp3", ignoreCase = true) -> "audio/mpeg"
            fileName.endsWith(".m4a", ignoreCase = true) -> "audio/mp4"
            fileName.endsWith(".webm", ignoreCase = true) -> "video/webm"
            else -> "*/*"
        }
    }

    private fun checkStoragePermissions() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            val permission = android.Manifest.permission.WRITE_EXTERNAL_STORAGE
            if (checkSelfPermission(permission) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
                requestPermissions(arrayOf(permission), 100)
            }
        }
    }

    override fun onBackPressed() {
        if (::webView.isInitialized && webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}
