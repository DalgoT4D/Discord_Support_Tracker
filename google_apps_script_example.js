/**
 * Google Apps Script to manage Discord support thread data in a spreadsheet
 * Handles three types of updates:
 * 1. Thread creation - Creates a new row for a support thread
 * 2. First response - Updates response time for an existing thread
 * 3. Resolution - Updates resolution time for an existing thread
 */

// Configuration
const SHEET_NAME = "Support Threads";

// Column indexes (0-based)
const COLS = {
  THREAD_ID: 0,
  TITLE: 1,
  TYPE: 2,
  RAISED_BY: 3,
  DATE: 4,
  FIRST_RESPONDED_BY: 5,
  TIME_TAKEN_TO_RESPOND: 6,
  TIME_TAKEN_TO_RESOLVE: 7,
  RESOLVED_DATE: 8,
  LINK: 9
};

/**
 * Process a POST request with thread data
 */
function doPost(e) {
  try {
    // Validate the event
    if (!e || !e.postData || !e.postData.contents) {
      logError("Invalid request: Missing or malformed POST data");
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "Missing or malformed POST data"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // Parse the JSON payload from Discord bot
    const payload = JSON.parse(e.postData.contents);
    logInfo("Received payload: " + JSON.stringify(payload));
    
    // Get the main spreadsheet and sheet
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = ss.getSheetByName(SHEET_NAME);
    
    // Create the sheet if it doesn't exist
    if (!sheet) {
      sheet = setupSheet();
    }
    
    // Process based on event type
    switch(payload.event_type) {
      case 'thread_created':
        processThreadCreation(sheet, payload);
        break;
      case 'thread_response':
        processThreadResponse(sheet, payload);
        break;
      case 'resolution':
        processThreadResolution(sheet, payload);
        break;
      default:
        logError(`Unknown event type: ${payload.event_type}`);
    }
    
    // Return success
    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      message: `Processed ${payload.event_type} event`
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch(error) {
    // Log any errors
    logError("Error processing request: " + error);
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      message: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Process a thread creation event
 */
function processThreadCreation(sheet, payload) {
  const thread_id = payload.thread_id;
  logInfo(`Processing thread creation: ${thread_id}`);
  
  // Check if thread already exists
  const rowIndex = findThreadRow(sheet, thread_id);
  
  // If thread exists, update it; otherwise create a new row
  if (rowIndex > 0) {
    logInfo(`Updating existing thread: ${thread_id}`);
    
    // Update existing row with new creation data
    const rowData = [
      thread_id,
      payload.title || "",
      payload.type || "General Issue",
      payload.author || "",
      payload.timestamp || new Date().toISOString(),
      "", // First responder (empty)
      "", // Time to respond (empty)
      "", // Time to resolve (empty)
      "", // Resolved date (empty)
      payload.thread_link || ""
    ];
    
    sheet.getRange(rowIndex, 1, 1, rowData.length).setValues([rowData]);
    
  } else {
    // Create a new row for this thread
    logInfo(`Creating new thread: ${thread_id}`);
    
    const rowData = [
      thread_id,
      payload.title || "",
      payload.type || "General Issue",
      payload.author || "",
      payload.timestamp || new Date().toISOString(),
      "", // First responder (empty)
      "", // Time to respond (empty)
      "", // Time to resolve (empty)
      "", // Resolved date (empty)
      payload.thread_link || ""
    ];
    
    // Get the last row with data
    const lastRow = Math.max(1, sheet.getLastRow());
    
    // Append the new row
    sheet.getRange(lastRow + 1, 1, 1, rowData.length).setValues([rowData]);
  }
}

/**
 * Process a thread response event (first response)
 */
function processThreadResponse(sheet, payload) {
  const thread_id = payload.thread_id;
  logInfo(`Processing response: ${thread_id}`);
  
  // Find the thread's row
  const rowIndex = findThreadRow(sheet, thread_id);
  
  if (rowIndex > 0) {
    // Get current data
    const rowData = sheet.getRange(rowIndex, 1, 1, 10).getValues()[0];
    
    // Only update if first_responded_by is empty (this is the first response)
    if (!rowData[COLS.FIRST_RESPONDED_BY]) {
      logInfo(`Recording first response: ${thread_id}`);
      
      // Calculate time difference between creation and response
      const creationTime = new Date(rowData[COLS.DATE]);
      const responseTime = new Date(payload.timestamp);
      const timeDiff = calculateTimeDiff(creationTime, responseTime);
      
      // Update first responder and time
      sheet.getRange(rowIndex, COLS.FIRST_RESPONDED_BY + 1).setValue(payload.author);
      sheet.getRange(rowIndex, COLS.TIME_TAKEN_TO_RESPOND + 1).setValue(timeDiff);
    } else {
      logInfo(`Thread already has first response: ${thread_id}`);
    }
  } else {
    // If thread doesn't exist yet, create it first
    logInfo(`Thread not found, creating with response data: ${thread_id}`);
    
    const newRowData = [
      thread_id,
      payload.title || "",
      payload.type || "General Issue",
      "", // Creator (unknown)
      payload.timestamp || new Date().toISOString(),
      payload.author || "",  // First responder 
      "N/A",  // Time to respond (N/A since we don't know creation time)
      "", // Time to resolve (empty)
      "", // Resolved date (empty)
      payload.thread_link || ""
    ];
    
    // Append the new row
    const lastRow = Math.max(1, sheet.getLastRow());
    sheet.getRange(lastRow + 1, 1, 1, newRowData.length).setValues([newRowData]);
  }
}

/**
 * Process a thread resolution event
 */
function processThreadResolution(sheet, payload) {
  const thread_id = payload.thread_id;
  logInfo(`Processing resolution: ${thread_id}`);
  
  // Find the thread's row
  const rowIndex = findThreadRow(sheet, thread_id);
  
  if (rowIndex > 0) {
    // Get current data
    const rowData = sheet.getRange(rowIndex, 1, 1, 10).getValues()[0];
    
    // Only update if not already resolved
    if (!rowData[COLS.TIME_TAKEN_TO_RESOLVE] || rowData[COLS.TIME_TAKEN_TO_RESOLVE] === "") {
      logInfo(`Recording resolution time: ${thread_id}`);
      
      // Calculate time difference between creation and resolution
      const creationTime = new Date(rowData[COLS.DATE]);
      const resolutionTime = new Date(payload.resolved_time);
      const timeDiff = calculateTimeDiff(creationTime, resolutionTime);
      
      // Update issue type if provided in the payload
      if (payload.type) {
        sheet.getRange(rowIndex, COLS.TYPE + 1).setValue(payload.type);
      }
      
      // Update resolution time and date
      sheet.getRange(rowIndex, COLS.TIME_TAKEN_TO_RESOLVE + 1).setValue(timeDiff);
      sheet.getRange(rowIndex, COLS.RESOLVED_DATE + 1).setValue(payload.resolved_time);
      
      // Update link if provided
      if (payload.thread_link && !rowData[COLS.LINK]) {
        sheet.getRange(rowIndex, COLS.LINK + 1).setValue(payload.thread_link);
      }
    } else {
      logInfo(`Thread already resolved: ${thread_id}`);
    }
    return;
  } else {
    // If thread doesn't exist yet, create it with resolution data
    logInfo(`Thread not found, creating with resolution data: ${thread_id}`);
    
    const newRowData = [
      thread_id,
      payload.title || "",
      payload.type || "Unknown", // Use provided type if available
      "Unknown", // Creator (unknown)
      new Date().toISOString(), // Using current time as we don't know creation time
      "", // First responder (empty)
      "", // Time to respond (empty)
      "N/A", // Time to resolve (we don't know accurate creation time)
      payload.resolved_time || new Date().toISOString(),
      payload.thread_link || ""  // Link if provided
    ];
    
    // Append the new row
    const lastRow = Math.max(1, sheet.getLastRow());
    sheet.getRange(lastRow + 1, 1, 1, newRowData.length).setValues([newRowData]);
  }
}

/**
 * Find a thread's row by thread_id
 * Returns the row index (1-based) or 0 if not found
 */
function findThreadRow(sheet, thread_id) {
  // Get all thread IDs from column A
  const lastRow = sheet.getLastRow();
  if (lastRow <= 1) {
    return 0; // Only header row exists
  }
  
  const threadIds = sheet.getRange(2, COLS.THREAD_ID + 1, lastRow - 1, 1).getValues();
  
  // Find the matching row
  for (let i = 0; i < threadIds.length; i++) {
    if (threadIds[i][0] === thread_id) {
      return i + 2; // Add 2 because arrays are 0-based and header row
    }
  }
  
  return 0; // Not found
}

/**
 * Calculate human-readable time difference between two dates
 */
function calculateTimeDiff(startDate, endDate) {
  if (!startDate || !endDate) {
    return "N/A";
  }
  
  // Get time difference in milliseconds
  const diffMs = endDate.getTime() - startDate.getTime();
  
  if (diffMs < 0) {
    return "N/A"; // Handle invalid time difference
  }
  
  // Convert to days, hours, minutes, seconds
  const diffSecs = Math.floor(diffMs / 1000);
  const days = Math.floor(diffSecs / 86400);
  const hours = Math.floor((diffSecs % 86400) / 3600);
  const minutes = Math.floor((diffSecs % 3600) / 60);
  const seconds = diffSecs % 60;
  
  if (days > 0) {
    return `${days}d ${hours}h ${minutes}m`;
  } else if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  } else {
    return `${seconds}s`;
  }
}

/**
 * Set up the spreadsheet structure
 */
function setupSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  
  // Create a new sheet if it doesn't exist
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
  }
  
  // Set up headers
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
    "link"
  ];
  
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  
  // Format header row
  sheet.getRange(1, 1, 1, headers.length).setFontWeight("bold");
  sheet.getRange(1, 1, 1, headers.length).setBackground("#E0E0E0");
  
  // Freeze header row
  sheet.setFrozenRows(1);
  
  // Auto-resize columns
  for (let i = 1; i <= headers.length; i++) {
    sheet.autoResizeColumn(i);
  }
  
  return sheet;
}

/**
 * Test function for thread creation
 */
function testThreadCreation() {
  const testPayload = {
    thread_id: "test123",
    title: "Test Support Thread",
    type: "Platform Issue",
    author: "TestUser#1234",
    timestamp: new Date().toISOString(),
    thread_link: "https://discord.com/channels/1234/5678",
    event_type: "thread_created"
  };
  
  // Create mock event
  const mockEvent = {
    postData: {
      contents: JSON.stringify(testPayload)
    }
  };
  
  // Call doPost with mock event
  const result = doPost(mockEvent);
  logInfo("Test thread creation result: " + result.getContent());
}

/**
 * Test function for first response
 */
function testFirstResponse() {
  const testPayload = {
    thread_id: "test123", // Use same ID as creation test
    title: "Test Support Thread",
    author: "Responder#5678",
    timestamp: new Date(new Date().getTime() + 3600000).toISOString(), // 1 hour later
    thread_link: "https://discord.com/channels/1234/5678",
    event_type: "thread_response"
  };
  
  // Create mock event
  const mockEvent = {
    postData: {
      contents: JSON.stringify(testPayload)
    }
  };
  
  // Call doPost with mock event
  const result = doPost(mockEvent);
  logInfo("Test first response result: " + result.getContent());
}

/**
 * Test function for resolution
 */
function testResolution() {
  const testPayload = {
    thread_id: "test123", // Use same ID as creation test
    title: "Test Support Thread",
    resolved_time: new Date(new Date().getTime() + 86400000).toISOString(), // 1 day later
    event_type: "resolution"
  };
  
  // Create mock event
  const mockEvent = {
    postData: {
      contents: JSON.stringify(testPayload)
    }
  };
  
  // Call doPost with mock event
  const result = doPost(mockEvent);
  logInfo("Test resolution result: " + result.getContent());
}

/**
 * Logger utility for info messages
 */
function logInfo(message) {
  Logger.log(`[INFO] ${message}`);
}

/**
 * Logger utility for error messages
 */
function logError(message) {
  Logger.log(`[ERROR] ${message}`);
  console.error(message);
}

/**
 * Handle GET requests - useful for testing the web app connection
 */
function doGet() {
  return ContentService.createTextOutput(
    "Discord Support Bot Webhook is active. This endpoint accepts POST requests only."
  );
} 