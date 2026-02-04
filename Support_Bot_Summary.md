# Discord Support Bot - Quick Reference

---

## Google Sheet Columns

| # | Column | What It Stores |
|---|--------|----------------|
| 1 | `thread_id` | Unique ID of the Discord thread |
| 2 | `title` | Thread title |
| 3 | `type` | Tags/categories (e.g., "Platform Issue, Bug") |
| 4 | `raised_by` | Who created the ticket |
| 5 | `date_created` | When ticket was created |
| 6 | `first_responded_by` | Who responded first from support team |
| 7 | `time_to_first_response` | How long until first response (e.g., "45m") |
| 8 | `time_to_resolution` | How long to resolve (e.g., "2d 4h") |
| 9 | `resolution_date` | When ticket was resolved |
| 10 | `link` | Direct link to Discord thread |
| 11 | `is_engineering` | TRUE = Engineering issue, FALSE = Consulting |
| 12 | `outside_business_hours` | TRUE = Created outside 9am-6pm IST |
| 13 | `reopen_count` | How many times ticket was reopened |
| 14 | `warning_message_id` | Internal ID for the resolved message |

---

## Flows - What Happens When

| Action | What the Bot Does |
|--------|-------------------|
| **NGO creates a thread** | New row added to sheet with title, creator, date, link |
| **Support team responds** | Records who responded first + time taken |
| **Tags added/changed/removed** | Updates `type` column with current tags |
| **Thread title edited** | Updates `title` column |
| **Thread marked "Resolved"** | Calculates resolution time, sends warning message tagging the NGO user |
| **Resolved tag removed (Reopened)** | Edits warning message to "Reopened", increments `reopen_count` |
| **Thread resolved again** | Sends new warning message, updates resolution time |
| **No response for 1 hour** | Sends ONE SLA alert to alert channels |

---

## Features Explained

| Feature | What It Means |
|---------|---------------|
| **Auto-logging** | Every new ticket automatically appears in the Google Sheet |
| **Response tracking** | We know who responded first and how quickly |
| **Tag sync** | Any tag changes in Discord reflect in the sheet |
| **Title sync** | Title changes in Discord reflect in the sheet |
| **Resolution warning** | When resolved, bot posts: "🔴 @user This thread is resolved. Create a new thread for new issues." |
| **Reopen detection** | If resolved tag is removed, bot edits the message to: "🟢 Thread reopened!" |
| **Reopen count** | Tracks how many times a ticket was reopened |
| **SLA alert** | If no one responds within 1 hour, bot alerts the team in specified channels |
| **Business hours flag** | Marks if ticket was created outside 9am-6pm IST |
| **Engineering flag** | Marks if it's an engineering issue or consulting request |

---

## Alert Messages

**When Resolved:**
```
🔴 @user This thread has been marked as RESOLVED.
We will no longer monitor this thread. Please create a new thread for new issues.
```

**When Reopened:**
```
🟢 This thread has been REOPENED! We're continuing the conversation here.
```

**SLA Alert (sent to alert channels):**
```
⚠️ SLA ALERT: Ticket "[Title]" has no response for 1 hour.
Raised by: [user] | Type: Engineering/Non-Engineering
Link: [thread link]
```

---

## Summary

1. NGO opens thread → Logged in sheet
2. Support responds → First responder + time recorded
3. Tags change → Sheet updated
4. Title changes → Sheet updated
5. Marked resolved → Warning sent, resolution time logged
6. Reopened → Warning edited, reopen count +1
7. 1 hour no response → SLA alert sent
