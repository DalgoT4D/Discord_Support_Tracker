/**
 * Google Apps Script for Discord Support Tracker Bot
 *
 * Handles the following events:
 * - thread_created: New support ticket created
 * - first_response: First response from support team
 * - tags_changed: Tags updated on thread
 * - title_changed: Thread title updated
 * - resolved: Thread marked as resolved
 * - reopened: Thread reopened (resolved tag removed)
 */

// Configuration
const SHEET_NAME = "Support Tickets";

// Column indexes (0-based) - matches PRD specification
const COLS = {
  THREAD_ID: 0,
  TITLE: 1,
  TYPE: 2,
  RAISED_BY: 3,
  DATE_CREATED: 4,
  FIRST_RESPONDED_BY: 5,
  TIME_TO_FIRST_RESPONSE: 6,
  TIME_TO_RESOLUTION: 7,
  RESOLUTION_DATE: 8,
  LINK: 9,
  IS_ENGINEERING: 10,
  OUTSIDE_BUSINESS_HOURS: 11,
  REOPEN_COUNT: 12,
  WARNING_MESSAGE_ID: 13,
  REOPEN_HISTORY: 14
};

const NUM_COLUMNS = 15;

/**
 * Process incoming POST requests from the Discord bot
 */
function doPost(e) {
  try {
    // Validate request
    if (!e) {
      logError("No event object received");
      return errorResponse("No event object received");
    }

    if (!e.postData) {
      logError("No postData in request");
      return errorResponse("No postData in request");
    }

    if (!e.postData.contents) {
      logError("No contents in postData");
      return errorResponse("No contents in postData");
    }

    // Parse JSON payload
    let payload;
    try {
      payload = JSON.parse(e.postData.contents);
    } catch (parseError) {
      logError(`JSON parse error: ${parseError.message}`);
      return errorResponse(`Invalid JSON: ${parseError.message}`);
    }

    // Validate required fields
    if (!payload.event_type) {
      logError("Missing event_type in payload");
      return errorResponse("Missing event_type in payload");
    }

    if (!payload.thread_id) {
      logError("Missing thread_id in payload");
      return errorResponse("Missing thread_id in payload");
    }

    logInfo(`Received: ${payload.event_type} for thread ${payload.thread_id}`);

    // Get or create sheet
    let sheet;
    try {
      const ss = SpreadsheetApp.getActiveSpreadsheet();
      if (!ss) {
        logError("Could not get active spreadsheet");
        return errorResponse("Could not get active spreadsheet");
      }

      sheet = ss.getSheetByName(SHEET_NAME);
      if (!sheet) {
        logInfo("Sheet not found, creating new sheet");
        sheet = setupSheet(ss);
      }
    } catch (sheetError) {
      logError(`Sheet access error: ${sheetError.message}`);
      return errorResponse(`Sheet access error: ${sheetError.message}`);
    }

    // Route to appropriate handler based on event type
    let result;
    try {
      switch (payload.event_type) {
        case 'thread_created':
          result = handleThreadCreated(sheet, payload);
          break;
        case 'first_response':
          result = handleFirstResponse(sheet, payload);
          break;
        case 'tags_changed':
          result = handleTagsChanged(sheet, payload);
          break;
        case 'title_changed':
          result = handleTitleChanged(sheet, payload);
          break;
        case 'resolved':
          result = handleResolved(sheet, payload);
          break;
        case 'reopened':
          result = handleReopened(sheet, payload);
          break;
        default:
          logError(`Unknown event type: ${payload.event_type}`);
          return errorResponse(`Unknown event type: ${payload.event_type}`);
      }
    } catch (handlerError) {
      logError(`Handler error for ${payload.event_type}: ${handlerError.message}`);
      return errorResponse(`Handler error: ${handlerError.message}`);
    }

    return successResponse(`Processed ${payload.event_type}`, result);

  } catch (error) {
    logError(`Unexpected error in doPost: ${error.message}\nStack: ${error.stack}`);
    return errorResponse(`Unexpected error: ${error.message}`);
  }
}

/**
 * Handle new thread creation
 */
function handleThreadCreated(sheet, payload) {
  try {
    const threadId = String(payload.thread_id);

    // Check if thread already exists (shouldn't happen, but safety check)
    const rowIndex = findThreadRow(sheet, threadId);
    if (rowIndex > 0) {
      logInfo(`Thread ${threadId} already exists at row ${rowIndex}, skipping creation`);
      return { action: "skipped", reason: "already_exists", row: rowIndex };
    }

    // Sanitize and validate input data
    const rowData = [
      threadId,
      sanitizeString(payload.title, ""),
      sanitizeString(payload.type, ""),
      sanitizeString(payload.raised_by, "Unknown"),
      sanitizeString(payload.date_created, new Date().toISOString()),
      "",  // first_responded_by
      "",  // time_to_first_response
      "",  // time_to_resolution
      "",  // resolution_date
      sanitizeString(payload.thread_link, ""),
      payload.is_engineering === true ? "TRUE" : "FALSE",
      payload.outside_business_hours === true ? "TRUE" : "FALSE",
      0,   // reopen_count
      "",  // warning_message_id
      ""   // reopen_history
    ];

    // Append new row
    const lastRow = Math.max(1, sheet.getLastRow());
    const newRowIndex = lastRow + 1;

    sheet.getRange(newRowIndex, 1, 1, rowData.length).setValues([rowData]);

    logInfo(`Created new thread: ${threadId} at row ${newRowIndex}`);
    return { action: "created", row: newRowIndex };

  } catch (error) {
    logError(`Error in handleThreadCreated: ${error.message}`);
    throw error;
  }
}

/**
 * Handle first response to a thread
 */
function handleFirstResponse(sheet, payload) {
  try {
    const threadId = String(payload.thread_id);
    const rowIndex = findThreadRow(sheet, threadId);

    if (rowIndex <= 0) {
      logError(`Thread not found for first response: ${threadId}`);
      return { action: "skipped", reason: "thread_not_found" };
    }

    // Get current row data
    let rowData;
    try {
      rowData = sheet.getRange(rowIndex, 1, 1, NUM_COLUMNS).getValues()[0];
    } catch (readError) {
      logError(`Error reading row ${rowIndex}: ${readError.message}`);
      throw readError;
    }

    // Only update if first_responded_by is empty
    if (rowData[COLS.FIRST_RESPONDED_BY] && String(rowData[COLS.FIRST_RESPONDED_BY]).trim() !== "") {
      logInfo(`Thread ${threadId} already has first response, skipping`);
      return { action: "skipped", reason: "already_responded" };
    }

    // Update first responder and time
    const responder = sanitizeString(payload.first_responded_by, "");
    const responseTime = sanitizeString(payload.time_to_first_response, "");

    sheet.getRange(rowIndex, COLS.FIRST_RESPONDED_BY + 1).setValue(responder);
    sheet.getRange(rowIndex, COLS.TIME_TO_FIRST_RESPONSE + 1).setValue(responseTime);

    logInfo(`Recorded first response for thread: ${threadId} by ${responder}`);
    return { action: "updated", row: rowIndex };

  } catch (error) {
    logError(`Error in handleFirstResponse: ${error.message}`);
    throw error;
  }
}

/**
 * Handle tags changed on a thread
 */
function handleTagsChanged(sheet, payload) {
  try {
    const threadId = String(payload.thread_id);
    const rowIndex = findThreadRow(sheet, threadId);

    if (rowIndex <= 0) {
      logError(`Thread not found for tags update: ${threadId}`);
      return { action: "skipped", reason: "thread_not_found" };
    }

    // Update the type column with new tags
    const newType = sanitizeString(payload.type, "");
    sheet.getRange(rowIndex, COLS.TYPE + 1).setValue(newType);

    logInfo(`Updated tags for thread: ${threadId} to "${newType}"`);
    return { action: "updated", row: rowIndex };

  } catch (error) {
    logError(`Error in handleTagsChanged: ${error.message}`);
    throw error;
  }
}

/**
 * Handle title changed on a thread
 */
function handleTitleChanged(sheet, payload) {
  try {
    const threadId = String(payload.thread_id);
    const rowIndex = findThreadRow(sheet, threadId);

    if (rowIndex <= 0) {
      logError(`Thread not found for title update: ${threadId}`);
      return { action: "skipped", reason: "thread_not_found" };
    }

    // Update the title column
    const newTitle = sanitizeString(payload.title, "");
    sheet.getRange(rowIndex, COLS.TITLE + 1).setValue(newTitle);

    logInfo(`Updated title for thread: ${threadId} to "${newTitle}"`);
    return { action: "updated", row: rowIndex };

  } catch (error) {
    logError(`Error in handleTitleChanged: ${error.message}`);
    throw error;
  }
}

/**
 * Handle thread marked as resolved
 */
function handleResolved(sheet, payload) {
  try {
    const threadId = String(payload.thread_id);
    const rowIndex = findThreadRow(sheet, threadId);

    if (rowIndex <= 0) {
      logError(`Thread not found for resolution: ${threadId}`);
      return { action: "skipped", reason: "thread_not_found" };
    }

    const resolutionDate = sanitizeString(payload.resolution_date, new Date().toISOString());
    const timeToResolution = sanitizeString(payload.time_to_resolution, "");
    const warningMessageId = sanitizeString(payload.warning_message_id, "");

    // Get current reopen count
    let reopenCount = 0;
    try {
      reopenCount = parseInt(sheet.getRange(rowIndex, COLS.REOPEN_COUNT + 1).getValue()) || 0;
    } catch (readError) {
      logError(`Error reading reopen count: ${readError.message}`);
    }

    if (reopenCount === 0) {
      // First resolution - update main columns
      sheet.getRange(rowIndex, COLS.RESOLUTION_DATE + 1).setValue(resolutionDate);
      sheet.getRange(rowIndex, COLS.TIME_TO_RESOLUTION + 1).setValue(timeToResolution);
    } else {
      // Subsequent resolution - calculate duration from reopen time, not original creation
      let currentHistory = "";
      try {
        currentHistory = String(sheet.getRange(rowIndex, COLS.REOPEN_HISTORY + 1).getValue() || "");
      } catch (readError) {
        logError(`Error reading reopen history: ${readError.message}`);
      }

      // Parse the last entry to get the reopen timestamp and calculate actual duration
      const lines = currentHistory.split('\n').filter(line => line.trim());
      if (lines.length > 0) {
        const lastLine = lines[lines.length - 1];
        // Extract the ISO timestamp from the last entry
        // Format: "N. Reopened: YYYY-MM-DD HH:MM:SS (pending)"
        const reopenMatch = lastLine.match(/Reopened:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})/);

        let actualDuration = timeToResolution; // fallback to bot-calculated time
        if (reopenMatch) {
          const reopenedAt = new Date(reopenMatch[1]);
          const resolvedAt = new Date(resolutionDate);
          const durationSeconds = (resolvedAt - reopenedAt) / 1000;
          actualDuration = formatDurationFromSeconds(durationSeconds);
        }

        // Update the last entry with resolution info
        const formattedResolveDate = formatDateForHistory(resolutionDate);
        const updatedLastLine = lastLine
          .replace(' (pending)', '')
          .replace(/,\s*Resolved:.*$/, '') + // Remove any existing resolved info
          `, Resolved: ${formattedResolveDate}, Duration: ${actualDuration}`;

        lines[lines.length - 1] = updatedLastLine;
        const updatedHistory = lines.join('\n');
        sheet.getRange(rowIndex, COLS.REOPEN_HISTORY + 1).setValue(updatedHistory);
      }
    }

    // Always update warning message ID
    sheet.getRange(rowIndex, COLS.WARNING_MESSAGE_ID + 1).setValue(warningMessageId);

    // Update tags if provided
    if (payload.type !== undefined && payload.type !== null) {
      sheet.getRange(rowIndex, COLS.TYPE + 1).setValue(sanitizeString(payload.type, ""));
    }

    logInfo(`Marked thread as resolved: ${threadId} (reopen_count: ${reopenCount})`);
    return { action: "resolved", row: rowIndex, is_reopen_resolution: reopenCount > 0 };

  } catch (error) {
    logError(`Error in handleResolved: ${error.message}`);
    throw error;
  }
}

/**
 * Handle thread reopened (resolved tag removed)
 */
function handleReopened(sheet, payload) {
  try {
    const threadId = String(payload.thread_id);
    const rowIndex = findThreadRow(sheet, threadId);

    if (rowIndex <= 0) {
      logError(`Thread not found for reopen: ${threadId}`);
      return { action: "skipped", reason: "thread_not_found" };
    }

    // Get current reopen count and increment
    let currentCount;
    try {
      currentCount = sheet.getRange(rowIndex, COLS.REOPEN_COUNT + 1).getValue();
    } catch (readError) {
      logError(`Error reading reopen count: ${readError.message}`);
      currentCount = 0;
    }

    const newCount = (parseInt(currentCount) || 0) + 1;
    sheet.getRange(rowIndex, COLS.REOPEN_COUNT + 1).setValue(newCount);

    // Get reopened timestamp - store full timestamp for duration calculation
    const reopenedAt = sanitizeString(payload.reopened_at, new Date().toISOString());
    // Convert to parseable format: "YYYY-MM-DD HH:MM:SS"
    const reopenDate = new Date(reopenedAt);
    const parseableTimestamp = Utilities.formatDate(reopenDate, Session.getScriptTimeZone(), "yyyy-MM-dd HH:mm:ss");
    const displayDate = formatDateForHistory(reopenedAt);

    let currentHistory = "";
    try {
      currentHistory = String(sheet.getRange(rowIndex, COLS.REOPEN_HISTORY + 1).getValue() || "");
    } catch (readError) {
      logError(`Error reading reopen history: ${readError.message}`);
    }

    // Create new numbered entry with full timestamp for calculation
    // Format: "N. Reopened: YYYY-MM-DD HH:MM:SS (pending)"
    // When resolved, "(pending)" will be replaced with ", Resolved: DATE, Duration: Xh Ym"
    const newEntry = `${newCount}. Reopened: ${parseableTimestamp} (pending)`;
    const updatedHistory = currentHistory ? `${currentHistory}\n${newEntry}` : newEntry;
    sheet.getRange(rowIndex, COLS.REOPEN_HISTORY + 1).setValue(updatedHistory);

    // NOTE: We no longer clear resolution_date and time_to_resolution
    // The original resolution time is preserved

    logInfo(`Reopened thread: ${threadId} (reopen count: ${newCount})`);
    return { action: "reopened", row: rowIndex, reopen_count: newCount };

  } catch (error) {
    logError(`Error in handleReopened: ${error.message}`);
    throw error;
  }
}

/**
 * Format date for reopen history (e.g., "Jan 18 10:30")
 */
function formatDateForHistory(isoDateString) {
  try {
    const date = new Date(isoDateString);
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const month = months[date.getMonth()];
    const day = date.getDate();
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${month} ${day} ${hours}:${minutes}`;
  } catch (error) {
    logError(`Error formatting date: ${error.message}`);
    return isoDateString;
  }
}

/**
 * Format duration from seconds to human-readable format (e.g., "2d 4h 15m" or "45m 30s")
 * Matches the Python bot's format_duration function
 */
function formatDurationFromSeconds(totalSeconds) {
  try {
    if (totalSeconds < 0) {
      return "0s";
    }

    totalSeconds = Math.floor(totalSeconds);
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;

    const parts = [];
    if (days > 0) {
      parts.push(`${days}d`);
    }
    if (hours > 0 || days > 0) {
      parts.push(`${hours}h`);
    }
    if (minutes > 0 || hours > 0 || days > 0) {
      parts.push(`${minutes}m`);
    }
    if (parts.length === 0 || (days === 0 && hours === 0)) {
      parts.push(`${secs}s`);
    }

    return parts.join(" ");
  } catch (error) {
    logError(`Error formatting duration: ${error.message}`);
    return "Unknown";
  }
}

/**
 * Find row index for a thread by thread_id
 * Returns row index (1-based) or 0 if not found
 */
function findThreadRow(sheet, threadId) {
  try {
    const lastRow = sheet.getLastRow();
    if (lastRow <= 1) {
      return 0;  // Only header row exists
    }

    // Get all thread IDs at once for efficiency
    const threadIds = sheet.getRange(2, COLS.THREAD_ID + 1, lastRow - 1, 1).getValues();
    const searchId = String(threadId);

    for (let i = 0; i < threadIds.length; i++) {
      if (String(threadIds[i][0]) === searchId) {
        return i + 2;  // +2 because: 0-indexed + header row
      }
    }

    return 0;  // Not found

  } catch (error) {
    logError(`Error in findThreadRow: ${error.message}`);
    return 0;
  }
}

/**
 * Sanitize string input to prevent injection and handle nulls
 */
function sanitizeString(value, defaultValue) {
  if (value === null || value === undefined) {
    return defaultValue;
  }
  // Convert to string and trim
  return String(value).trim();
}

/**
 * Set up the spreadsheet with headers
 */
function setupSheet(ss) {
  try {
    let sheet = ss.getSheetByName(SHEET_NAME);
    if (!sheet) {
      sheet = ss.insertSheet(SHEET_NAME);
    }

    const headers = [
      "thread_id",
      "title",
      "type",
      "raised_by",
      "date_created",
      "first_responded_by",
      "time_to_first_response",
      "time_to_resolution",
      "resolution_date",
      "link",
      "is_engineering",
      "outside_business_hours",
      "reopen_count",
      "warning_message_id",
      "reopen_history"
    ];

    // Set headers
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);

    // Format header row
    const headerRange = sheet.getRange(1, 1, 1, headers.length);
    headerRange.setFontWeight("bold");
    headerRange.setBackground("#4a86e8");
    headerRange.setFontColor("#ffffff");
    headerRange.setHorizontalAlignment("center");

    // Freeze header row
    sheet.setFrozenRows(1);

    // Set column widths for better readability
    const columnWidths = {
      1: 120,   // thread_id
      2: 250,   // title
      3: 150,   // type
      4: 150,   // raised_by
      5: 150,   // date_created
      6: 150,   // first_responded_by
      7: 120,   // time_to_first_response
      8: 120,   // time_to_resolution
      9: 150,   // resolution_date
      10: 200,  // link
      11: 100,  // is_engineering
      12: 130,  // outside_business_hours
      13: 100,  // reopen_count
      14: 150,  // warning_message_id
      15: 300   // reopen_history
    };

    for (const [col, width] of Object.entries(columnWidths)) {
      sheet.setColumnWidth(parseInt(col), width);
    }

    logInfo("Sheet setup complete");
    return sheet;

  } catch (error) {
    logError(`Error in setupSheet: ${error.message}`);
    throw error;
  }
}

/**
 * Success response helper
 */
function successResponse(message, data) {
  const response = {
    status: "success",
    message: message,
    timestamp: new Date().toISOString()
  };

  if (data) {
    response.data = data;
  }

  return ContentService.createTextOutput(JSON.stringify(response))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Error response helper
 */
function errorResponse(message) {
  const response = {
    status: "error",
    message: message,
    timestamp: new Date().toISOString()
  };

  return ContentService.createTextOutput(JSON.stringify(response))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Logging helpers
 */
function logInfo(message) {
  const timestamp = new Date().toISOString();
  Logger.log(`[INFO] ${timestamp} - ${message}`);
}

function logError(message) {
  const timestamp = new Date().toISOString();
  Logger.log(`[ERROR] ${timestamp} - ${message}`);
  console.error(`[ERROR] ${timestamp} - ${message}`);
}

/**
 * Handle GET requests - for testing connection
 */
function doGet() {
  return ContentService.createTextOutput(JSON.stringify({
    status: "ok",
    message: "Discord Support Tracker Webhook is active. Send POST requests to log tickets.",
    timestamp: new Date().toISOString(),
    version: "2.0"
  })).setMimeType(ContentService.MimeType.JSON);
}

/**
 * Manual trigger to set up the sheet (run this first time)
 */
function initializeSheet() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = setupSheet(ss);
    logInfo(`Sheet initialized: ${sheet.getName()}`);
    return "Sheet initialized successfully";
  } catch (error) {
    logError(`Failed to initialize sheet: ${error.message}`);
    return `Error: ${error.message}`;
  }
}

// ============================================
// TEST FUNCTIONS (for debugging)
// ============================================

function testThreadCreation() {
  const payload = {
    event_type: "thread_created",
    thread_id: "test_" + Date.now(),
    title: "Test Support Ticket",
    type: "Platform Issue, Bug",
    raised_by: "testuser#1234",
    date_created: new Date().toISOString(),
    thread_link: "https://discord.com/channels/123/456",
    is_engineering: true,
    outside_business_hours: false
  };

  const mockEvent = { postData: { contents: JSON.stringify(payload) } };
  const result = doPost(mockEvent);
  logInfo("Test result: " + result.getContent());
}

function testFirstResponse() {
  // First create a thread
  const threadId = "test_response_" + Date.now();
  const createPayload = {
    event_type: "thread_created",
    thread_id: threadId,
    title: "Test Thread for Response",
    raised_by: "creator#1234",
    date_created: new Date().toISOString(),
    is_engineering: true,
    outside_business_hours: false
  };

  doPost({ postData: { contents: JSON.stringify(createPayload) } });

  // Then add first response
  const responsePayload = {
    event_type: "first_response",
    thread_id: threadId,
    first_responded_by: "support#5678",
    time_to_first_response: "25m 30s"
  };

  const mockEvent = { postData: { contents: JSON.stringify(responsePayload) } };
  const result = doPost(mockEvent);
  logInfo("Test result: " + result.getContent());
}

function testResolution() {
  // First create a thread
  const threadId = "test_resolve_" + Date.now();
  const createPayload = {
    event_type: "thread_created",
    thread_id: threadId,
    title: "Test Thread for Resolution",
    raised_by: "creator#1234",
    date_created: new Date().toISOString(),
    is_engineering: true,
    outside_business_hours: false
  };

  doPost({ postData: { contents: JSON.stringify(createPayload) } });

  // Then resolve it
  const resolvePayload = {
    event_type: "resolved",
    thread_id: threadId,
    resolution_date: new Date().toISOString(),
    time_to_resolution: "2d 4h 15m",
    warning_message_id: "msg_123456",
    type: "Platform Issue, Bug, resolved"
  };

  const mockEvent = { postData: { contents: JSON.stringify(resolvePayload) } };
  const result = doPost(mockEvent);
  logInfo("Test result: " + result.getContent());
}

function testReopen() {
  // First create and resolve a thread
  const threadId = "test_reopen_" + Date.now();

  doPost({
    postData: {
      contents: JSON.stringify({
        event_type: "thread_created",
        thread_id: threadId,
        title: "Test Thread for Reopen",
        raised_by: "creator#1234",
        date_created: new Date().toISOString(),
        is_engineering: true,
        outside_business_hours: false
      })
    }
  });

  doPost({
    postData: {
      contents: JSON.stringify({
        event_type: "resolved",
        thread_id: threadId,
        resolution_date: new Date().toISOString(),
        time_to_resolution: "1h 30m"
      })
    }
  });

  // Then reopen it
  const reopenPayload = {
    event_type: "reopened",
    thread_id: threadId,
    reopened_at: new Date().toISOString()
  };

  doPost({ postData: { contents: JSON.stringify(reopenPayload) } });
  logInfo("Reopened thread: " + threadId);

  // Wait a bit and resolve again - duration should be calculated from reopen time
  Utilities.sleep(2000); // 2 seconds for testing

  const resolveAgainPayload = {
    event_type: "resolved",
    thread_id: threadId,
    resolution_date: new Date().toISOString(),
    time_to_resolution: "should_be_ignored_for_reopen"
  };

  const result = doPost({ postData: { contents: JSON.stringify(resolveAgainPayload) } });
  logInfo("Test reopen/resolve result: " + result.getContent());
}

function testMultipleReopens() {
  // Test multiple reopen/resolve cycles
  const threadId = "test_multi_reopen_" + Date.now();

  // Create thread
  doPost({
    postData: {
      contents: JSON.stringify({
        event_type: "thread_created",
        thread_id: threadId,
        title: "Test Multiple Reopens",
        raised_by: "creator#1234",
        date_created: new Date().toISOString(),
        is_engineering: true,
        outside_business_hours: false
      })
    }
  });

  // First resolution
  doPost({
    postData: {
      contents: JSON.stringify({
        event_type: "resolved",
        thread_id: threadId,
        resolution_date: new Date().toISOString(),
        time_to_resolution: "2h 15m"
      })
    }
  });
  logInfo("First resolution done");

  // First reopen
  Utilities.sleep(1000);
  doPost({
    postData: {
      contents: JSON.stringify({
        event_type: "reopened",
        thread_id: threadId,
        reopened_at: new Date().toISOString()
      })
    }
  });
  logInfo("First reopen done");

  // Second resolution (from reopen)
  Utilities.sleep(2000);
  doPost({
    postData: {
      contents: JSON.stringify({
        event_type: "resolved",
        thread_id: threadId,
        resolution_date: new Date().toISOString(),
        time_to_resolution: "ignored"
      })
    }
  });
  logInfo("Second resolution done");

  // Second reopen
  Utilities.sleep(1000);
  doPost({
    postData: {
      contents: JSON.stringify({
        event_type: "reopened",
        thread_id: threadId,
        reopened_at: new Date().toISOString()
      })
    }
  });
  logInfo("Second reopen done");

  // Third resolution (from reopen)
  Utilities.sleep(3000);
  doPost({
    postData: {
      contents: JSON.stringify({
        event_type: "resolved",
        thread_id: threadId,
        resolution_date: new Date().toISOString(),
        time_to_resolution: "ignored"
      })
    }
  });
  logInfo("Third resolution done - check reopen_history column for:");
  logInfo("Expected format:");
  logInfo("1. Reopened: YYYY-MM-DD HH:MM:SS, Resolved: DATE, Duration: Xs");
  logInfo("2. Reopened: YYYY-MM-DD HH:MM:SS, Resolved: DATE, Duration: Xs");
}

function testInvalidPayload() {
  // Test with missing event_type
  const mockEvent1 = { postData: { contents: JSON.stringify({ thread_id: "123" }) } };
  logInfo("Test missing event_type: " + doPost(mockEvent1).getContent());

  // Test with invalid JSON
  const mockEvent2 = { postData: { contents: "not valid json" } };
  logInfo("Test invalid JSON: " + doPost(mockEvent2).getContent());

  // Test with missing postData
  const mockEvent3 = {};
  logInfo("Test missing postData: " + doPost(mockEvent3).getContent());
}
