# Discord Support Tracker Bot - Product Requirements Document (PRD)

**Version:** 2.0
**Last Updated:** February 2026
**Author:** Dalgo Engineering Team

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Solution Overview](#3-solution-overview)
4. [User Roles](#4-user-roles)
5. [User Flows](#5-user-flows)
6. [Google Sheet Structure](#6-google-sheet-structure)
7. [Bot Behaviors & Triggers](#7-bot-behaviors--triggers)
8. [Alerts & Notifications](#8-alerts--notifications)
9. [Business Rules](#9-business-rules)
10. [Example Scenarios](#10-example-scenarios)
11. [Technical Requirements](#11-technical-requirements)
12. [Future Enhancements](#12-future-enhancements)

---

## 1. Executive Summary

The **Discord Support Tracker Bot** is an automated system that tracks all support tickets raised by NGOs in our Discord support channel. It automatically logs ticket information to a Google Sheet, tracks response times, sends alerts for unattended tickets, and manages ticket lifecycle (open → resolved → reopened).

### Key Benefits

| Benefit | Description |
|---------|-------------|
| **Automatic Tracking** | No manual data entry - everything is logged automatically |
| **Response Time Visibility** | Know how quickly the team responds to tickets |
| **SLA Monitoring** | Get alerts when tickets are unattended for too long |
| **Resolution Tracking** | Track how long it takes to resolve issues |
| **Clear Communication** | Users are notified when their ticket is resolved or reopened |

---

## 2. Problem Statement

### Current Challenges

1. **No visibility into support volume** - We don't know how many tickets we receive daily/weekly
2. **No response time tracking** - We can't measure how quickly we respond to NGOs
3. **Tickets fall through cracks** - Some tickets go unnoticed and unanswered
4. **No resolution tracking** - We don't know average time to resolve issues
5. **Manual tracking is tedious** - Support team has to manually log everything

### Impact

- NGOs may feel ignored if tickets aren't responded to promptly
- No data to improve support processes
- Can't identify which issue types are most common
- Can't measure team performance

---

## 3. Solution Overview

### How It Works (Simple Explanation)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DISCORD SUPPORT CHANNEL                      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                              BOT WATCHES                             │
│                                                                      │
│   👀 New ticket created?  ──────────────►  📝 Log to Google Sheet   │
│   👀 Someone responded?   ──────────────►  📝 Update response time  │
│   👀 Tags changed?        ──────────────►  📝 Update issue type     │
│   👀 Title changed?       ──────────────►  📝 Update title          │
│   👀 Marked resolved?     ──────────────►  📝 Log resolution time   │
│                                           📢 Notify user            │
│   👀 Reopened?            ──────────────►  📝 Update reopen count   │
│                                           📢 Update notification    │
│   ⏰ 1 hour passed?       ──────────────►  🚨 Send SLA alert        │
│      (no response)                                                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           GOOGLE SHEET                               │
│                                                                      │
│   All ticket data stored for reporting and analysis                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. User Roles

### 4.1 NGO Users (Ticket Creators)

- Create support tickets by posting in the Discord support forum
- Receive notifications when their ticket is resolved
- Can continue conversation if ticket is reopened

### 4.2 Support Team (Responders)

- Respond to tickets in Discord
- Add/remove tags to categorize issues
- Mark tickets as "resolved" when complete
- Can reopen tickets by removing the "resolved" tag

### 4.3 Managers (Viewers)

- View the Google Sheet for reporting
- Monitor SLA compliance
- Analyze support trends

---

## 5. User Flows

### 5.1 Flow: NGO Creates a New Ticket

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: NGO posts a message in the support forum channel         │
│         (This automatically creates a new thread/ticket)         │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: Bot detects the new thread and:                          │
│         ✓ Creates a new row in Google Sheet                      │
│         ✓ Records: Thread ID, Title, Creator, Date/Time, Link    │
│         ✓ Checks if created during business hours (9am-6pm IST)  │
│         ✓ Determines if it's an engineering issue                │
│         ✓ Adds ✅ reaction to confirm tracking                    │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 3: Bot starts a 1-hour timer for SLA monitoring             │
└──────────────────────────────────────────────────────────────────┘
```

**What the NGO sees:**
- Their message gets a ✅ reaction (confirms the bot tracked it)

**What gets logged:**
- New row in Google Sheet with ticket details

---

### 5.2 Flow: Support Team Responds to a Ticket

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: Support team member posts a reply in the thread          │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: Bot detects the response and checks:                     │
│         → Is this the FIRST response? (not from ticket creator)  │
└──────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            ┌─────────────┐      ┌─────────────────┐
            │ FIRST       │      │ NOT FIRST       │
            │ RESPONSE    │      │ RESPONSE        │
            └─────────────┘      └─────────────────┘
                    │                   │
                    ▼                   ▼
┌──────────────────────────┐    ┌──────────────────┐
│ Bot updates sheet:       │    │ Bot does nothing │
│ ✓ First Responded By     │    │ (already tracked)│
│ ✓ Time to First Response │    └──────────────────┘
│ ✓ Cancels SLA alert      │
└──────────────────────────┘
```

**What gets logged (first response only):**
- Who responded first
- How long it took to respond (e.g., "45m 30s")

---

### 5.3 Flow: Support Team Adds/Changes Tags

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: Support team adds, removes, or changes tags on thread    │
│         Examples: "Platform Issue", "Service Request", "Bug"     │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: Bot detects the tag change and:                          │
│         ✓ Updates the "type" column in Google Sheet              │
│         ✓ Records all current tags (comma-separated)             │
└──────────────────────────────────────────────────────────────────┘
```

**Example:**
- Tags changed from "General" to "Platform Issue, High Priority"
- Sheet updates: `type` = "Platform Issue, High Priority"

---

### 5.4 Flow: Support Team Changes Thread Title

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: Support team edits the thread title                      │
│         Example: "Help needed" → "Login issue - Org ABC"         │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: Bot detects the title change and:                        │
│         ✓ Updates the "title" column in Google Sheet             │
└──────────────────────────────────────────────────────────────────┘
```

---

### 5.5 Flow: Ticket Marked as Resolved

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: Support team adds "resolved" tag to the thread           │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: Bot detects the resolved tag and:                        │
│                                                                  │
│  📝 UPDATES GOOGLE SHEET:                                        │
│     ✓ Resolution Date                                            │
│     ✓ Time to Resolution (e.g., "2d 4h 15m")                     │
│     ✓ Stores warning message ID                                  │
│                                                                  │
│  📢 SENDS WARNING MESSAGE IN THREAD:                             │
│     ┌────────────────────────────────────────────────────────┐   │
│     │ 🔴 @username This thread has been marked as RESOLVED.  │   │
│     │                                                        │   │
│     │ We will no longer monitor this thread for new          │   │
│     │ messages. If you have a new issue or follow-up         │   │
│     │ question, please create a new thread.                  │   │
│     │                                                        │   │
│     │ Thank you for reaching out to Dalgo Support!           │   │
│     └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

**What the NGO sees:**
- A message tagging them, informing the ticket is closed

**What gets logged:**
- Resolution date and time
- Total time from creation to resolution

---

### 5.6 Flow: Ticket Reopened

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: Support team REMOVES the "resolved" tag from thread      │
│         (This means the ticket needs more work)                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: Bot detects the tag removal and:                         │
│                                                                  │
│  📝 UPDATES GOOGLE SHEET:                                        │
│     ✓ Increments reopen_count by 1                               │
│                                                                  │
│  📢 EDITS THE WARNING MESSAGE TO:                                │
│     ┌────────────────────────────────────────────────────────┐   │
│     │ 🟢 UPDATE: This thread has been REOPENED!              │   │
│     │                                                        │   │
│     │ We're continuing the conversation here. Our support    │   │
│     │ team will follow up shortly.                           │   │
│     └────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

**What the NGO sees:**
- The previous "resolved" message changes to show the ticket is reopened

---

### 5.7 Flow: Ticket Re-Resolved (After Being Reopened)

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: Support team adds "resolved" tag again                   │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: Bot detects this is a RE-resolution and:                 │
│                                                                  │
│  📝 UPDATES GOOGLE SHEET:                                        │
│     ✓ Updates resolution date to new date                        │
│     ✓ Recalculates time to resolution                            │
│     ✓ Stores new warning message ID                              │
│                                                                  │
│  📢 SENDS NEW WARNING MESSAGE (same as 5.5)                      │
└──────────────────────────────────────────────────────────────────┘
```

---

### 5.8 Flow: SLA Alert (No Response in 1 Hour)

```
┌──────────────────────────────────────────────────────────────────┐
│ CONDITION: A ticket has been open for 1 hour with NO response    │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│ Bot sends ONE alert to the designated alert channels:            │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ ⚠️ SLA ALERT: Ticket Awaiting Response                     │  │
│  │                                                            │  │
│  │ 📋 Title: "Unable to login to dashboard"                   │  │
│  │ 👤 Raised by: user@ngo.org                                 │  │
│  │ ⏰ Waiting: 1 hour                                         │  │
│  │ 🏷️ Type: Engineering Issue                                 │  │
│  │ 🔗 Link: [Click to view](discord-link)                     │  │
│  │                                                            │  │
│  │ Please respond to this ticket as soon as possible.         │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

**Important Notes:**
- Only ONE alert is sent per ticket (not repeated)
- Alert is sent even if ticket was created outside business hours
- Alert includes whether it's an engineering issue or not

---

## 6. Google Sheet Structure

### 6.1 Column Definitions

| # | Column Name | Description | Example Value | Auto-Filled? |
|---|-------------|-------------|---------------|--------------|
| 1 | `thread_id` | Unique Discord thread identifier | 1234567890 | ✅ Yes |
| 2 | `title` | Thread title (updated if changed) | "Login issue - Org ABC" | ✅ Yes |
| 3 | `type` | Issue category from tags | "Platform Issue, Bug" | ✅ Yes |
| 4 | `raised_by` | Discord username of ticket creator | "john_ngo#1234" | ✅ Yes |
| 5 | `date_created` | When ticket was created | "2026-02-04 10:30:00" | ✅ Yes |
| 6 | `first_responded_by` | Who responded first | "support_sarah#5678" | ✅ Yes |
| 7 | `time_to_first_response` | Time until first response | "45m 30s" | ✅ Yes |
| 8 | `time_to_resolution` | Total time to resolve | "2d 4h 15m" | ✅ Yes |
| 9 | `resolution_date` | When marked resolved | "2026-02-06 14:45:00" | ✅ Yes |
| 10 | `link` | Direct link to Discord thread | https://discord.com/... | ✅ Yes |
| 11 | `team` | Team assignment based on tag | Engineering / Consulting / (empty) | ✅ Yes |
| 12 | `outside_business_hours` | Created outside 9am-6pm IST? | TRUE / FALSE | ✅ Yes |
| 13 | `reopen_count` | Times ticket was reopened | 0, 1, 2... | ✅ Yes |
| 14 | `warning_message_id` | ID of the resolve warning message | 9876543210 | ✅ Yes |

### 6.2 Sample Data

| thread_id | title | type | raised_by | date_created | first_responded_by | time_to_first_response | time_to_resolution | resolution_date | link | team | outside_business_hours | reopen_count | warning_message_id |
|-----------|-------|------|-----------|--------------|-------------------|----------------------|-------------------|-----------------|------|------|----------------------|--------------|-------------------|
| 111222333 | Dashboard not loading | Platform Issue, Engineering | ngo_user#1234 | 2026-02-04 10:30:00 | support#5678 | 25m 10s | 1d 2h 30m | 2026-02-05 13:00:00 | https://... | Engineering | FALSE | 0 | 444555666 |
| 222333444 | Need training session | Service Request, Consulting | org_admin#4321 | 2026-02-04 20:15:00 | support#5678 | 13h 45m 0s | 2d 0h 0m | 2026-02-06 20:15:00 | https://... | Consulting | TRUE | 1 | 555666777 |

### 6.3 Time Format Examples

| Duration | Format |
|----------|--------|
| Less than 1 hour | "45m 30s" |
| 1-24 hours | "2h 15m" |
| More than 1 day | "2d 4h 15m" |

---

## 7. Bot Behaviors & Triggers

### 7.1 Summary Table

| Trigger Event | Bot Action | Sheet Update |
|---------------|------------|--------------|
| New thread created | Log ticket, add ✅ reaction, start SLA timer | New row created |
| First response (not from creator) | Record responder and time | `first_responded_by`, `time_to_first_response` |
| Subsequent responses | Nothing | None |
| Tag added/removed/changed | Update issue type | `type` |
| Title changed | Update title | `title` |
| "Resolved" tag added | Send warning message, log resolution | `resolution_date`, `time_to_resolution`, `warning_message_id` |
| "Resolved" tag removed | Edit warning to "reopened" | `reopen_count` |
| 1 hour passes with no response | Send SLA alert to channels | None |

### 7.2 What Triggers Sheet Updates

| When This Happens... | These Columns Get Updated |
|----------------------|---------------------------|
| Thread created | `thread_id`, `title`, `type`, `raised_by`, `date_created`, `link`, `team`, `outside_business_hours` |
| First response | `first_responded_by`, `time_to_first_response` |
| Tags changed | `type` |
| Title changed | `title` |
| Resolved | `resolution_date`, `time_to_resolution`, `warning_message_id`, `type` |
| Reopened | `reopen_count` |
| Re-resolved | `resolution_date`, `time_to_resolution`, `warning_message_id` |

---

## 8. Alerts & Notifications

### 8.1 SLA Alert

**When:** A ticket has no response for 1 hour

**Where:** Sent to alert channels (configured in environment)

**Frequency:** ONE time only per ticket

**Content:**
```
⚠️ SLA ALERT: Ticket Awaiting Response

📋 Title: [Thread Title]
👤 Raised by: [Username]
⏰ Waiting: 1 hour
🏷️ Team: [Engineering / Consulting / Unassigned]
🔗 Link: [Discord Thread Link]

Please respond to this ticket as soon as possible.
```

### 8.2 Resolution Warning Message (In Thread)

**When:** Thread is marked as resolved

**Where:** Posted in the thread itself

**Content:**
```
🔴 @username This thread has been marked as RESOLVED.

We will no longer monitor this thread for new messages.
If you have a new issue or follow-up question, please create a new thread.

Thank you for reaching out to Dalgo Support!
```

### 8.3 Reopened Message (Edited In Thread)

**When:** Resolved tag is removed

**Where:** Edits the previous warning message

**Content:**
```
🟢 UPDATE: This thread has been REOPENED!

We're continuing the conversation here.
Our support team will follow up shortly.
```

---

## 9. Business Rules

### 9.1 Business Hours

| Setting | Value |
|---------|-------|
| Start Time | 9:00 AM IST |
| End Time | 6:00 PM IST |
| Days | Monday to Friday |

**Note:** Business hours are only used to mark the `outside_business_hours` column. SLA alerts are sent regardless of business hours.

### 9.2 Team Classification

Team is assigned based on Discord forum tags:

| Tag | Team Value |
|-----|------------|
| Contains "Engineering" | `Engineering` |
| Contains "Consulting" | `Consulting` |
| Neither | (empty) |

### 9.3 First Response Rules

- Only human messages count (bot messages are ignored)
- The ticket creator's messages don't count as "responses"
- Only the FIRST response is tracked; subsequent responses are ignored
- Time is calculated from ticket creation to first response

### 9.4 Resolution Rules

- Resolution happens when "resolved" tag is added
- Time to resolution is calculated from creation to resolution
- If ticket is reopened and re-resolved, times are recalculated

---

## 10. Example Scenarios

### Scenario 1: Happy Path (Quick Resolution)

| Time | Action | Sheet Update |
|------|--------|--------------|
| 10:00 AM | NGO creates ticket: "Dashboard not loading" | New row created |
| 10:25 AM | Support responds: "Let me check this" | `first_responded_by` = support, `time_to_first_response` = "25m" |
| 10:45 AM | Support adds "Platform Issue" tag | `type` = "Platform Issue, resolved" |
| 10:45 AM | Support adds "resolved" tag | `resolution_date` = 10:45, `time_to_resolution` = "45m" |
| 10:45 AM | Bot sends resolved warning to NGO | `warning_message_id` stored |

### Scenario 2: Ticket Reopened

| Time | Action | Sheet Update |
|------|--------|--------------|
| Day 1, 10:00 AM | NGO creates ticket | New row |
| Day 1, 10:30 AM | Support responds | First response tracked |
| Day 1, 11:00 AM | Marked resolved | Resolution tracked, warning sent |
| Day 2, 2:00 PM | NGO says "Issue came back" | None |
| Day 2, 2:15 PM | Support removes "resolved" tag | `reopen_count` = 1, warning edited |
| Day 2, 4:00 PM | Marked resolved again | New resolution time, new warning |

### Scenario 3: SLA Breach

| Time | Action | Alert |
|------|--------|-------|
| 10:00 AM | NGO creates ticket | SLA timer starts |
| 11:00 AM | No response yet | ⚠️ SLA alert sent to channels |
| 11:30 AM | Support finally responds | (No more alerts) |

### Scenario 4: After-Hours Ticket

| Time | Action | Sheet Update |
|------|--------|--------------|
| 8:00 PM (after hours) | NGO creates ticket | `outside_business_hours` = TRUE |
| 9:00 PM | 1 hour passes, no response | ⚠️ SLA alert sent |
| 9:30 AM next day | Support responds | First response tracked (13h 30m) |

---

## 11. Technical Requirements

### 11.1 Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Bot authentication token | `MTIz...abc` |
| `SUPPORT_CHANNEL_ID` | Forum channel to monitor | `1234567890` |
| `WEBHOOK_URL` | Google Apps Script endpoint | `https://script.google.com/...` |
| `ALERT_CHANNEL_IDS` | Channels for SLA alerts (comma-separated) | `111222333,444555666` |

### 11.2 Discord Bot Permissions Required

- Read Messages
- Send Messages
- Read Message History
- Add Reactions
- View Channels

### 11.3 Google Sheet Requirements

- Google Sheet with appropriate sharing settings
- Google Apps Script deployed as web app
- Web app set to "Anyone" can access

---

## 12. Future Enhancements

These features are planned for future versions:

| Feature | Description | Priority |
|---------|-------------|----------|
| NGO Selection | Dropdown/input to select organization name | Medium |
| Response Count | Track total number of messages in thread | Low |
| Assignee Tracking | Track who is working on the ticket | Low |
| Satisfaction Survey | Ask NGO if issue was resolved satisfactorily | Low |
| Auto-Tagging | Automatically suggest tags based on keywords | Low |
| Dashboard | Visual dashboard for support metrics | Medium |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Jan 2026 | Initial bot with basic tracking |
| 2.0 | Feb 2026 | Added: SLA alerts, reopen tracking, title updates, business hours, improved resolution flow |

---

## Questions?

Contact the Dalgo Engineering team for any clarifications about this document.
