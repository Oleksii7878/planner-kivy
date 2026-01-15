[app]
title = Planner
package.name = planner
package.domain = org.oleksii

source.dir = .
source.include_exts = py

requirements = python3,kivy

orientation = portrait
fullscreen = 1

android.permissions = INTERNET

android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b

android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
