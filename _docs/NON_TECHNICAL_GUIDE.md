# CCMD Bot Master - Non-Technical User Guide

## 🎯 For People Who Don't Know Coding

### Don't Worry - This is Easy!

This guide is written for people who have **never coded before** and don't want to learn. Everything is designed to be **click-and-go** with clear instructions.

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Open the Easy Update Manager
1. **Double-click** `easy_update_manager.py`
2. **Wait** for the window to open
3. **You'll see 4 tabs** at the top - that's your main menu

### Step 2: Add Your First Computer
1. **Click the "📋 Manage Computers" tab**
2. **Fill in the form** with computer details:
   - **Computer Name**: "John's Computer" (any friendly name)
   - **IP Address**: "192.168.1.100" (ask IT for this)
   - **User**: "John Smith" (who uses this computer)
   - **Bot Path**: Click "Browse" and find where the bot files are
3. **Click "➕ Add New Computer"**
4. **Repeat** for each computer in your office

### Step 3: Create Your First Update
1. **Click the "📦 Create Updates" tab**
2. **Fill in the form**:
   - **Source Folder**: Click "Browse" and select your updated bot files
   - **Version**: "1.1.0" (just make it higher than before)
   - **Changes**: "Fixed the counselor assignment bug"
3. **Click "📦 Create Update Package"**
4. **Wait** for it to finish (you'll see progress)

### Step 4: Deploy the Update
1. **Click the "🚀 Deploy Updates" tab**
2. **Select** the update package you just created
3. **Select** which computers to update (or click "Select All")
4. **Click "🚀 Deploy Update"**
5. **Watch** the progress as it updates each computer

### Step 5: Check Everything Worked
1. **Click the "📊 Monitor Status" tab**
2. **Click "🔍 Check All Computer Status"**
3. **Make sure** all computers show "Online" status

---

## 📋 What Each Tab Does

### 📋 Manage Computers
**What it does**: Adds and manages all the computers that will get updates

**When to use**: 
- When you get a new computer in the office
- When someone's computer changes
- When you need to remove a computer

**How to use**:
1. Fill in the form with computer details
2. Click "Add New Computer"
3. The computer appears in the list below

### 📦 Create Updates
**What it does**: Packages your updated bot files into an update package

**When to use**:
- After you make changes to the bot files
- When you want to send bug fixes to everyone
- When you add new features

**How to use**:
1. Make your changes to the bot files first
2. Fill in the form with update details
3. Click "Create Update Package"
4. Wait for it to finish

### 🚀 Deploy Updates
**What it does**: Sends update packages to all the computers

**When to use**:
- After you create an update package
- When you want to update everyone's computers
- When you need to fix a bug quickly

**How to use**:
1. Select an update package from the dropdown
2. Choose which computers to update
3. Click "Deploy Update"
4. Watch the progress

### 📊 Monitor Status
**What it does**: Shows you the status of all computers and recent updates

**When to use**:
- To check if all computers are working
- To see if updates were successful
- To troubleshoot problems

**How to use**:
1. Click "Check All Computer Status"
2. Look at the status table
3. Check the log for any errors

---

## 🔧 Common Tasks

### Adding a New Computer
**Note**: Computers are now automatically registered when they install the bot software. You typically don't need to add them manually.

If you need to add a computer manually:
1. **Get the computer details** from IT:
   - IP Address
   - User name
   - Where the bot files are located
2. **Open Easy Update Manager** (enter password: `Integritycode1!`)
3. **Go to "📋 Manage Computers" tab**
4. **Fill in the form** and click "Add New Computer"

### Fixing a Bug
1. **Make the fix** to the bot files on your computer
2. **Open Easy Update Manager** (enter password: `Integritycode1!`)
3. **Go to "📦 Create Updates" tab**
4. **Create an update package** with the fix
5. **Go to "🚀 Deploy Updates" tab**
6. **Select which computers to update** (use checkboxes to select individual computers or click "Select All")
7. **Deploy the update** to selected computers

### Adding a New Feature
1. **Add the new feature** to the bot files
2. **Test it thoroughly** on your computer
3. **Open Easy Update Manager** (enter password: `Integritycode1!`)
4. **Create an update package** with the new feature
5. **Deploy it** to selected computers (use checkboxes to choose which computers get the update)
6. **Monitor the status** to make sure it worked

### Running Bots Sequentially
The **Counselor Assignment Bot** has a built-in checkbox to automatically run the **Intake & Referral Bot** after completion:
1. **Open the Counselor Assignment Bot**
2. **Check the box**: "🚀 Run Intake & Referral Bot After Counselor Assignment"
3. **Run the bot** - it will automatically launch the Intake & Referral Bot when finished
4. **Both bots will use the same credentials and CSV data**

### Checking if Everyone is Up to Date
1. **Open Easy Update Manager** (enter password: `Integritycode1!`)
2. **Go to "📊 Monitor Status" tab**
3. **Click "Check All Computer Status"**
4. **Look at the "Version" column** - everyone should have the same version

---

## 🚨 Troubleshooting

### "Access Denied" Error
**Problem**: Easy Update Manager shows "Access Denied" and won't let you enter a password
**Solution**: 
- Make sure you're running the Easy Update Manager as an administrator
- Try right-clicking on `easy_update_manager.py` and selecting "Run as administrator"
- The password is: `Integritycode1!`

### "I Can't Add a Computer"
**Problem**: The form won't let you add a computer
**Solution**: 
- Make sure all fields are filled in
- Check that the IP address is correct
- **Note**: Computers are automatically registered when they install the bot software
- Verify the bot path exists

### "Update Package Won't Create"
**Problem**: The update package creation fails
**Solution**:
- Make sure the source folder exists
- Check that you have write permissions
- Try a different version number

### "Deployment Fails"
**Problem**: Some computers don't get the update
**Solution**:
- Check if the computers are online
- Verify network connectivity
- Try deploying to one computer at a time

### "Computers Show as Offline"
**Problem**: Status check shows computers as offline
**Solution**:
- Check if computers are turned on
- Verify network connection
- Ask IT to check the IP addresses

---

## 💡 Tips for Success

### Before You Start
- **Get a list** of all computers from IT
- **Find out** where bot files are located on each computer
- **Test** the process with one computer first

### When Creating Updates
- **Always test** your changes first
- **Use clear version numbers** (1.0.0, 1.1.0, 1.2.0)
- **Describe changes clearly** in the changes field

### When Deploying
- **Deploy to a few computers first** to test
- **Wait for feedback** before deploying to everyone
- **Monitor the status** after deployment

### Regular Maintenance
- **Check computer status** weekly
- **Keep track** of which computers have which version
- **Update computers** that are behind

---

## 📞 Getting Help

### If You're Stuck
1. **Check the instructions** in each tab
2. **Look at the log messages** for error details
3. **Try the troubleshooting section** above
4. **Contact IT support** with specific error messages

### What Information to Provide
When asking for help, include:
- **What you were trying to do**
- **What error message you saw**
- **Which tab you were using**
- **What you clicked before the error**

### Common Error Messages
- **"Computer not found"**: Check the IP address
- **"Package not found"**: Make sure you created an update package first
- **"Access denied"**: Check file permissions
- **"Network error"**: Check internet connection

---

## 🎉 Success Stories

### "I Fixed a Bug in 5 Minutes"
*"I found a bug in the counselor assignment bot. I fixed it on my computer, created an update package, and deployed it to all 20 computers in our office. Everyone had the fix within 10 minutes!"*

### "Added a New Feature Easily"
*"We needed a new report feature. I added it to the bot, created an update package, and deployed it. All employees got the new feature the same day!"*

### "No More Manual Updates"
*"Before this system, I had to visit each computer to update the bots. Now I can update all computers from my desk in minutes!"*

---

## ✅ Quick Reference

### Daily Tasks
- [ ] Check computer status
- [ ] Look for any offline computers
- [ ] Verify all computers have the latest version

### Weekly Tasks
- [ ] Review deployment logs
- [ ] Check for any error messages
- [ ] Plan any upcoming updates

### Monthly Tasks
- [ ] Update the computer list
- [ ] Review and clean up old update packages
- [ ] Test the update process with a new computer

---

## 🚀 You're Ready!

### Remember:
- **Everything is click-and-go** - no coding required
- **Clear instructions** are in each tab
- **Error messages** tell you what went wrong
- **Help is available** if you get stuck

### Start Small:
1. **Add one computer** to test
2. **Create a small update** to practice
3. **Deploy to that one computer** first
4. **Once you're comfortable**, add more computers

### You've Got This!
The system is designed to be **intuitive and easy**. If you can use a computer, you can manage bot updates. Don't be afraid to try - the worst that can happen is you ask for help!

---

*This guide is written for non-technical users. If you need more technical details, check the other documentation files.*
