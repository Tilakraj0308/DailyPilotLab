# TwinMind Local Setup Guide

This guide covers setting up the TwinMind React Native app to run locally on an Android Emulator or a Physical Android Device.

## Running on an Android Emulator

1. **Install Android Studio** and set up an Android Virtual Device (AVD).
2. **Start the Emulator** from the Device Manager in Android Studio, or via the command line:
   ```bash
   emulator -avd <Your_AVD_Name>
   ```
3. **Start the Metro Bundler**:
   ```bash
   npm start
   ```
4. **Compile and run the App** in a separate terminal window:
   ```bash
   npm run android
   ```

## Running on a Physical Device via USB

If you want to run the app directly on your physical Android device via a USB connection, follow these steps:

### 1. Enable USB Debugging on Your Device
1. Go to **Settings > About Phone** and tap on **Build Number** 7 times to enable Developer Options.
2. Go to **Settings > System > Developer Options** (or simply Developer Options in the main menu).
3. Turn on **USB Debugging**.
4. Connect your device to your computer via USB.
5. A prompt will appear on your phone asking to "Allow USB debugging". Check "Always allow from this computer" and click **OK**.

### 2. Verify Your Device is Connected
Run the following command in your terminal:
```bash
adb devices
```
You should see your device listed as `attached`. If the list is empty, ensure your connection is secure or try changing the USB connection mode to "File Transfer (MTP)" or "PTP".

### 3. Port Forwarding for the Metro Bundler
To prevent "unable to load script" or connection errors to the Metro bundler over USB:
```bash
adb reverse tcp:8081 tcp:8081
```
*Note: Run this command every time you reconnect the device via USB.*

### 4. Start the Application
1. **Start the Metro Bundler**:
   ```bash
   npm start
   ```
2. **Compile and run the App** in a separate terminal:
   ```bash
   npm run android
   ```

### Troubleshooting
- If you see a red error screen saying the app cannot connect to the Metro bundler, try running the `adb reverse` command again, make sure `npm start` is still running, and reload the app from the Developer Menu on your device (shake the device to open it).
- If you disconnect your phone and want to debug it over Wi-Fi later, you will need to open your phone's Developer Menu, go to **Settings > Debug server host & port for device**, and enter your computer's local IP address (e.g. `192.168.1.5:8081`).
