# Veritas & Varieties Read Me

**Veritas & Varieties** is a platform designed to simplify event discovery for students and residents in Boston. By aggregating event information from emails and displaying it on an interactive calendar, the platform helps users stay informed and engaged with their community.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Setup Instructions](#setup-instructions)
4. [Usage Guide](#usage-guide)
5. [Technologies Used](#technologies-used)
6. [Known Issues](#known-issues)
7. [Future Improvements](#future-improvements)

---

## Overview

Veritas & Varieties automates the process of event discovery for Harvard students in the Boston area. Emails from various organizations are processed using the Gmail API to fetch email content and Gemini AI to extract event details, which are then stored in a SQLite database. These events are displayed via an interactive website featuring a calendar and other user-friendly views.
We originally set this project up utilizing a particular email account that received information from sources in the Boston area, however, those parts of the code have been cleared, so this can be altered to collect information about whatever location you'd like!

The primary functionality includes four main steps:

1. Gmail API integration to fetch emails from an inbox, designed to only process unread emails and to mark them as "read" after access. 
2. Gemini AI API to extract event details such as date, name, time, location, price, and description from email content. These are formatted to fit into the current database, but if you're interested in changing the database, can be altered through the query!
3. A database which takes in events from the Gemini API 
4. A web interface to explore and interact with the event data. 

---

## Features

1. **Automated Event Aggregation**: Uses Gmail and Gemini APIs to extract events from email content and store them in a database. Besides occasionally having to refresh permissions on the email account and having to keep track of usage of Google Cloud, very little human involvement is needed!
2. **Interactive Calendar**: Browse events by month, week, or date using a dynamic calendar. Find a "random" event using the random event feature! Feel free to substitute our HTML design for something that would fit your organization's needs.
3. **Database Management**: Automatically cleans outdated or incomplete events and ensures no duplicate entries are displayed to users.
4. **User-Friendly Interface**: Provides intuitive navigation and multiple ways to explore events, including a "Random Event" button.
5. **Threaded Backend**: Processes backend tasks in parallel to ensure the website loads without delays. May need to reload webpage 30 seconds after opening the website to ensure up-to-date events, since the API calls have a bit of latency.

---

## Setup Instructions

### Installation

Ensure the following Python packages are installed:

```
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
pip install ratelimit
pip install google-generativeai
pip install flask
pip install cs50
```

### Initial Setup

1. **Google API Setup**:

   - Enable the Gmail API in your Google Cloud account.
   - Download the `credentials.json` file and place it in the project directory.
   - Run the application locally using VSCode to generate the `token.json` file. (See the "IMPORTANT" note in the code. This can't be run through an online compiler because it requires a local server for proper access.)

2. **Environment Variables**:

   - Set the Gemini API key as an environment variable:
     ```bash
     export GEMINI_API_KEY="your_gemini_api_key"
     ```

3. **Database Setup**:

   - Ensure the SQLite database `events.db` is present and configured with the required schema for storing event data. We chose to remove our preset one since it may make sense to configure the database to your own needs.
   - Modify the query to the Google Gemini to ensure that the events are outputted in the format you need. 

### Running the Application

- Start the Flask server:
  ```bash
  flask run
  ```
- Open the website on the local port displayed in the terminal.

---

## Usage Guide

1. **Homepage**:

   - View a list of events happening on the current day.
   - The backend automatically updates the database by fetching and processing emails.

2. **Calendar View**:

   - Navigate through months to explore upcoming events.
   - Hover over events in the calendar to see details like price.

3. **Week View**:

   - Displays events grouped by each day of the week.

4. **Random Event**:

   - Click the "Random" button to view a randomly selected event.

---

## Technologies Used

- **Backend**: Python (Flask framework)
- **APIs**:
  - Gmail API for email fetching and processing
  - Gemini AI API for extracting event details
- **Database**: SQLite
- **Frontend**: HTML, CSS, Bootstrap, and Jinja templates
- **Concurrency**: Python threading for backend tasks

---

## Known Issues

1. **API Rate Limits**: The free tiers of Gmail and Gemini APIs limit the number of calls that can be made.
2. **Scaling**: The application currently supports a single inbox and a limited volume of events.
3. **Google Cloud Permissions**: You must configure your own goolge cloud permissions and ensure that they do not expire. We have set the call rate-limiting below the paid level.

---

## Future Improvements

1. **User Preferences**: Allow users to filter events by category, such as music, sports, or educational.
2. **Calendar Sync**: Integrate with Google Calendar for better event management.
3. **Scalability**: Expand support for multiple users and larger datasets.
4. **Enhanced Automation**: Finalize full Gmail API integration to eliminate manual steps like uploading email content.

---

Thank you for using Veritas & Varieties!
