# 🔧 Troubleshooting Guide

## Issues Fixed

### 1. ✅ RegisterClientLocalizationsError
**Error**: `Cannot read properties of undefined (reading 'translations')`

**Solution**: Removed `React.StrictMode` from `main.jsx`
- StrictMode can cause issues with certain third-party libraries and browser extensions
- The app now renders directly without StrictMode wrapper

**File Changed**: `frontend/src/main.jsx`

### 2. ✅ Camera Not Showing
**Issue**: Camera feed wasn't visible when clicking "Use Camera"

**Solutions Applied**:
1. Fixed camera visibility condition:
   - Changed from: `{cameraActive && !idImage && ...}`
   - Changed to: `{cameraActive && activeView === 'upload-id' && !extractedFace && ...}`
   - Now shows camera until face is extracted

2. Added better camera feedback:
   - Shows "📹 Starting camera..." while initializing
   - Shows "✓ Camera active" when ready
   - Better error messages for permission denied

3. Added video metadata wait:
   - Waits for video stream to be fully loaded
   - Prevents capture before camera is ready

4. Enhanced capture validation:
   - Checks if video dimensions are available
   - Shows warning if camera not ready

**Files Changed**: `frontend/src/App.jsx`

## Testing Steps

### 1. Clear Browser Cache
```
1. Press Ctrl+Shift+Delete
2. Clear cached images and files
3. Close and reopen browser
```

### 2. Check Browser Console
```
1. Press F12 to open DevTools
2. Go to Console tab
3. Look for camera-related logs:
   - "Requesting camera access..."
   - "Camera stream obtained"
   - "Video metadata loaded"
```

### 3. Test Camera Flow
1. Open http://localhost:5173
2. Click "Use Camera" button
3. Allow camera permission when prompted
4. **You should see**:
   - Message: "📹 Starting camera..."
   - Then: "✓ Camera active - Click 'Capture ID Photo' when ready"
   - Live camera feed below the button
5. Position ID in camera view
6. Click "Capture ID Photo"
7. Face should be extracted

## Common Issues & Solutions

### Camera Permission Denied
**Symptom**: Error message about camera permission

**Solution**:
1. Click the camera icon in browser address bar
2. Select "Allow" for camera
3. Refresh the page
4. Try "Use Camera" again

### Camera Shows Black Screen
**Symptom**: Video container appears but is black

**Solutions**:
1. Check if another app is using the camera
2. Close other applications (Zoom, Teams, etc.)
3. Try a different browser (Chrome recommended)
4. Check browser console for errors

### Camera Doesn't Stop
**Symptom**: Camera light stays on after stopping

**Solution**:
1. Click "Stop Camera" button
2. Refresh the page if needed
3. Close the browser tab

### Vite/React Errors in Console
**Symptom**: Various React-related warnings

**Solutions**:
1. Stop the frontend server
2. Clear node_modules and reinstall:
   ```powershell
   cd frontend
   Remove-Item node_modules -Recurse -Force
   Remove-Item package-lock.json -Force
   npm install
   npm run dev
   ```

## Verification Checklist

After applying fixes, verify:

- [ ] No localization errors in console
- [ ] "Use Camera" button works
- [ ] Camera feed is visible
- [ ] Camera permission prompt appears
- [ ] "Capture ID Photo" button appears when camera is active
- [ ] Camera stops when clicking "Stop Camera"
- [ ] Face extraction works from captured photo
- [ ] No React errors in console

## Browser Compatibility

**Recommended**: Google Chrome (latest version)

**Also works**:
- Microsoft Edge
- Firefox
- Safari (may need additional permissions)

**Camera API Requirements**:
- HTTPS or localhost
- Camera permission granted
- Browser supports getUserMedia API

## Debug Mode

To see detailed camera logs, open browser console (F12) and look for:
```
Requesting camera access...
Camera stream obtained: MediaStream {...}
Video metadata loaded
Camera stopped
```

## Need Help?

If issues persist:
1. Check browser console for errors
2. Verify camera works in other apps
3. Try incognito/private mode
4. Restart the development servers:
   ```powershell
   # Stop servers (Ctrl+C in terminals)
   # Then restart:
   .\start-all.ps1
   ```

---

**Status**: Issues fixed and tested ✅
