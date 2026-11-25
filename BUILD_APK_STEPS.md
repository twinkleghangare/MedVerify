# Building the MedVerify Android app (APK)

This is a [Capacitor](https://capacitorjs.com/) project — it wraps
`www/index.html` (the exact same frontend as `frontend/index.html` and
`docs/index.html`, just copied here for the app bundle) in a native Android
shell so it can be installed and run like a normal app, with its own icon,
splash screen, and no browser address bar.

**Important — this could not be built into an actual `.apk` file in the
environment that put this project together**, because building an Android
app requires downloading the Gradle build tool and the Android SDK from
Google's servers, and that environment only had network access to a small
allowlist of domains (GitHub, npm, PyPI) — not Google's or Gradle's
servers. Everything up to the actual build step (the web content, the
Capacitor/Android project structure, the manifest, permissions) was set up
and is correct — you just need to run the actual build yourself, which
only takes a few steps.

## What you need (one-time setup)

1. **Android Studio** — download from https://developer.android.com/studio
   (free). Installing it also installs the Android SDK and a bundled JDK,
   which is the easiest way to get everything you need in one go.
2. **Node.js** — download from https://nodejs.org (free) if you don't
   already have it. Needed for the Capacitor CLI.

## Steps

**1. Install dependencies**

Open a terminal in this `mobile-app/` folder:

```cmd
npm install
```

**2. Sync the web content into the native project**

This copies `www/` into the Android project's assets (only needed again
if you change `www/index.html` later):

```cmd
npx cap sync android
```

**3. Open the project in Android Studio**

```cmd
npx cap open android
```

This launches Android Studio with the project already loaded. First open
can take a while — Android Studio will download any missing SDK
components automatically (this is the step that needed network access to
Google's servers).

**4. Build the APK**

In Android Studio: **Build → Build Bundle(s) / APK(s) → Build APK(s)**.

Once it finishes, click the **"locate"** link in the notification that
appears (or find it manually at
`mobile-app/android/app/build/outputs/apk/debug/app-debug.apk`).

**5. Install it on your phone**

- Copy `app-debug.apk` to your phone (USB, email, Google Drive, whatever's
  easiest), then open it on the phone to install. You'll need to allow
  "install from unknown sources" for whichever app you used to open the
  file — Android will prompt you for this the first time.
- Or, with your phone connected via USB and USB debugging enabled
  (Settings → About phone → tap "Build number" 7 times → Developer
  options → USB debugging), click the green **Run ▶** button in Android
  Studio to install and launch it directly.

## Using the app

- On first launch, it tries to connect to the backend URL baked in as the
  default (the deployed Render backend — works out of the box over the
  internet, no setup needed).
- If you ever need to point it at a different backend (e.g. one you're
  running locally on your PC for testing), tap **"Change"** in the footer
  and enter the new address. This is saved on the device, so you don't
  need to rebuild the app to change it — just don't use `localhost` here,
  since on the phone that means "the phone itself," not your PC. Use your
  PC's local network IP (e.g. `http://192.168.1.5:8000`) if testing
  against a locally-running backend on the same Wi-Fi, or any public
  `https://` URL.

## Known limitations

- **This APK is unsigned** (a debug build) — fine for installing on your
  own phone or sharing directly with a few people, but Google Play Store
  submission requires a signed release build, which is a separate,
  more involved process (see Android Studio's **Build → Generate Signed
  Bundle / APK** if you want to go that route later).
- **Camera/gallery access for the photo-upload feature** relies on the
  system file picker, which Capacitor's WebView handles automatically for
  a standard `<input type="file">` — this should work out of the box, but
  wasn't tested on a real device in the environment that set this up (no
  Android device/emulator was available there either).
