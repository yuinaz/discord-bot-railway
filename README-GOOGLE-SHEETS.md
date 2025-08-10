# Webhook Google Sheets (Apps Script)

1. Buka Google Drive → **New → Apps Script**. Paste kode berikut ke `Code.gs`:

```javascript
const TOKEN = 'REPLACE_WITH_YOUR_SECRET_TOKEN'; // samakan dgn env bot

function ensureHeader_(sheet, header) {
  const firstRow = sheet.getRange(1,1,1,header.length).getValues()[0];
  const hasHeader = firstRow.filter(String).length > 0;
  if (!hasHeader) sheet.getRange(1,1,1,header.length).setValues([header]);
}

function appendObject_(sheet, obj) {
  const header = Object.keys(obj);
  ensureHeader_(sheet, header);
  const existingHeader = sheet.getRange(1,1,1,header.length).getValues()[0];
  const row = existingHeader.map(k => (k in obj ? obj[k] : ''));
  sheet.appendRow(row);
}

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    if (!body || body.token !== TOKEN) {
      return ContentService.createTextOutput(JSON.stringify({ok:false, error:'unauthorized'}))
        .setMimeType(ContentService.MimeType.JSON);
    }
    const type = body.type || 'generic';
    const sheetName = body.sheet || type || 'Inbox';
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = ss.getSheetByName(sheetName) || ss.insertSheet(sheetName);

    delete body.token;
    delete body.sheet;
    body.received_at = new Date().toISOString();

    appendObject_(sheet, body);
    return ContentService.createTextOutput(JSON.stringify({ok:true}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ok:false, error:String(err)}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
```

2. **Deploy → Web app**: Execute as *Me*, access *Anyone with the link*. Salin Web app URL → set sebagai `SHEETS_WEBHOOK_URL` di Render.

3. Tambah environment variables di Render:
- `SHEETS_WEBHOOK_URL`: URL Web App Apps Script
- `SHEETS_TOKEN`: secret yang sama dengan `TOKEN` di script

## Sheet Tabs yang disarankan
- **SystemMetrics**: `timestamp, guild_id, cpu_percent, ram_percent, proc_mem_mb, uptime_s`
- **Commands**: `timestamp, guild_id, user_id, command, status, duration_ms`
- **Bans**: `timestamp, guild_id, target_id, action, moderator_id, reason`
- **Members** *(opsional)*: `timestamp, guild_id, user_id, event`
- **Moderation** *(opsional)*: `timestamp, guild_id, actor_id, target_id, action, reason`
