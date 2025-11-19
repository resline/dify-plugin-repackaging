# Deploy Fix for 502 Errors on Coolify

## Problem
The application deployed on Coolify is experiencing 502 Bad Gateway errors when:
1. Uploading files and clicking "Start Repackaging"
2. Accessing various API endpoints like `/tasks` and `/tasks/completed`

## Root Cause
The 502 errors are caused by:
1. Nginx proxy timeout settings being too short for file processing operations
2. Backend uvicorn server not having proper keep-alive timeout
3. Possible Redis connection issues causing health check failures

## Fix Applied
1. **Updated nginx configuration** in `frontend/nginx.conf`:
   - Added `client_max_body_size 100M` for file uploads
   - Added proxy timeouts of 600s
   - Added request buffering disabled for uploads
   - Added retry logic for failed requests

2. **Updated backend command** in `docker-compose.yml` and `Dockerfile.all-in-one`:
   - Added `--timeout-keep-alive 600` to uvicorn command

## Steps to Apply Fix on Coolify

### Option 1: Force Rebuild (Recommended)
1. Go to Coolify dashboard
2. Navigate to the dify-plugin-repackaging application
3. Click "Force Rebuild" or "Redeploy" button
4. Wait for the build to complete

### Option 2: Manual Update
1. SSH into the Coolify server
2. Find the running container: `docker ps | grep dify-plugin`
3. Check if latest changes are applied:
   ```bash
   docker exec <container_id> cat /etc/nginx/nginx.conf | grep proxy_read_timeout
   ```
4. If not updated, force a new deployment

### Option 3: Clear Build Cache
1. In Coolify settings for the app
2. Enable "Clear Build Cache" option
3. Trigger a new deployment

## Verification
After deployment, verify the fix:
1. Check nginx config has proper timeouts
2. Check uvicorn is running with `--timeout-keep-alive 600`
3. Test file upload functionality
4. Monitor logs for any Redis connection issues

## Additional Notes
- The `Dockerfile.all-in-one` already has proper nginx timeouts (1800s)
- If issues persist, check Redis connectivity and health check endpoint
- Monitor container logs for any startup issues