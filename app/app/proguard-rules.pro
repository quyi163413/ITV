# Keep custom attributes
-keepattributes *Annotation*,SourceFile,LineNumberTable

# Keep ExoPlayer
-keep class androidx.media3.** { *; }
-dontwarn androidx.media3.**

# Keep OkHttp
-keep class okhttp3.** { *; }
-dontwarn okhttp3.**

# Keep Kotlin reflection
-keep class kotlin.reflect.** { *; }
-keep class kotlin.Metadata { *; }

# Keep our own classes
-keep class com.example.tvplayer.** { *; }
-keepclassmembers class com.example.tvplayer.** { *; }
