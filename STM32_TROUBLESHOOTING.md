# STM32 OTA Connection Troubleshooting

## Issue: HTTPSEND:FAIL with Status Code 0

Your device logs show the HTTP request is failing at the connection level before reaching the server.

### Possible Causes

1. **SSL/TLS Certificate Verification**
   - The device's HTTP client might not trust Vercel's SSL certificate
   - Solution: Configure the device to skip certificate verification (for testing) or load Vercel's root CA

2. **Connection Timeout**
   - Serverless functions can have cold starts (3-5 seconds)
   - Your device might have a shorter timeout
   - Solution: Increase the device's HTTP timeout to 60+ seconds

3. **Missing SSL Configuration in AT Commands**
   - Some LTE modules require explicit SSL configuration
   - Solution: Add AT commands for SSL setup

### Recommended Fixes

#### Option 1: Test with HTTP (Non-SSL) - For Debugging Only
Create a test domain without SSL enforcement:
```c
#define OTA_SERVER_URL "http://flask-ota-server.vercel.app"  // Remove 'https'
```
⚠️ **WARNING:** This is for testing only. Do NOT use in production.

#### Option 2: Configure SSL in Your STM32 Code
Before calling HTTP commands, add SSL configuration:

```c
// Add these AT commands before HTTPINIT
send_AT_command("AT+CSSLCFG=\"sslversion\",0,3");  // TLS 1.2
send_AT_command("AT+CSSLCFG=\"ignorelocaltime\",0,1");  // Ignore time check
send_AT_command("AT+SHSSL=0,\"\"");  // Use default SSL settings

// Then initialize HTTP
send_AT_command("AT+HTTPINIT");
```

#### Option 3: Increase Timeout
In your `send_AT_command_http` function, increase the timeout:
```c
#define HTTP_RESPONSE_TIMEOUT 90000  // 90 seconds instead of 60
```

#### Option 4: Use Simpler URL Format
Try connecting to the root health check first:
```c
#define TEST_URL "https://flask-ota-server.vercel.app/health"
```

### Testing Steps

1. **Test Basic Connectivity:**
   ```
   GET https://flask-ota-server.vercel.app/health
   ```
   This is a simple GET request with no body/headers.

2. **Test Echo Endpoint:**
   ```
   POST https://flask-ota-server.vercel.app/debug/echo
   Body: {"test":"hello"}
   ```
   This will echo back your request to verify everything is received.

3. **Check Vercel Logs:**
   - Go to https://vercel.com
   - Select `flask-ota-server` project
   - Click "Logs" tab
   - Look for incoming requests from your device's IP

### Compare with Working Django Backend

Since your device works with the Django backend, compare:

1. **URL Format:**
   - Django: `https://smart-solar-django-backend-git-dev0-360watts-projects.vercel.app/api/...`
   - OTA: `https://flask-ota-server.vercel.app/api/...`

2. **AT Command Sequence:**
   - Use the EXACT same AT command sequence that works with Django
   - Compare: HTTPINIT, HTTPURL, HTTPADDHEAD, HTTPCONTENT, HTTPREQUEST

3. **SSL Configuration:**
   - Check if Django endpoint has different SSL settings
   - Verify both use standard Vercel SSL certificates

### Quick Test Command for STM32

Add this test function to your firmware:
```c
void test_ota_server_connectivity() {
    // Test 1: Simple GET to health endpoint
    lte_http_client_set_url("https://flask-ota-server.vercel.app/health");
    lte_http_client_send_request("GET", NULL, 0);
    
    // Test 2: Debug echo
    lte_http_client_set_url("https://flask-ota-server.vercel.app/debug/echo");
    const char* test_body = "{\"test\":\"connectivity\"}";
    lte_http_client_send_request("POST", test_body, strlen(test_body));
}
```

### Expected Behavior

If connection succeeds, you should see in Vercel logs:
```
REQUEST: POST /api/ota/devices/C9B247344F1F/check
HEADERS: {Content-Type: application/json, Content-Length: 272, ...}
BODY: {"device_id":"C9B247344F1F",...}
```

If you DON'T see these logs, the request never reached the server (SSL/connection issue).
