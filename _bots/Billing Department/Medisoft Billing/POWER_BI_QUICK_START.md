# Power BI Quick Start Guide - Therapy Notes Focus

## 🚀 Get Started in 30 Minutes

This is a simplified, focused guide to get you up and running with Power BI using **Therapy Notes** as your primary data source.

---

## Step 1: Download Power BI Desktop (5 minutes)

1. Go to: **https://powerbi.microsoft.com/desktop/**
2. Click **"Download free"** button
3. Run the installer (accept defaults)
4. Launch Power BI Desktop

**That's it!** Power BI Desktop is completely free for creating reports.

---

## Step 2: Export Data from Therapy Notes (10 minutes)

Since **Therapy Notes is your primary system**, we'll start here:

### Export These Key Reports:

1. **Log into Therapy Notes** web portal

2. **Navigate to Reports** section

3. **Export to Excel** (last 30 days to start):
   - **Accounts Receivable Aging Report**
     - Export → Save as: `TN_AR_2024_01_15.xlsx`
   - **Revenue Report** (by date range)
     - Export → Save as: `TN_Revenue_2024_01_15.xlsx`
   - **Payment Report** (cash collections)
     - Export → Save as: `TN_Payments_2024_01_15.xlsx`

4. **Save all files to one folder**:
   - Create folder: `C:\PowerBIData\TherapyNotes\`
   - Save all exports there

**Tip**: Use consistent naming: `TN_ReportType_YYYY_MM_DD.xlsx`

---

## Step 3: Import into Power BI (10 minutes)

### Import Your First Report (AR Aging):

1. **Open Power BI Desktop**

2. **Click "Get Data"** (top left ribbon)

3. **Select "Excel"**

4. **Navigate to your Therapy Notes export**:
   - Go to: `C:\PowerBIData\TherapyNotes\`
   - Select: `TN_AR_2024_01_15.xlsx`

5. **Preview your data**:
   - Select the worksheet with your data
   - Click **"Load"** (or "Transform Data" if you need to clean it)

6. **Your data is now in Power BI!** ✅

### Import Additional Reports:

Repeat steps 2-5 for:
- Revenue Report
- Payment Report

---

## Step 4: Create Your First Dashboard (15 minutes)

### Create 5 Key Financial Metrics:

#### Metric 1: Total Accounts Receivable

1. **In the Fields panel** (right side), find your A/R amount column
2. **Drag** it to the canvas
3. Power BI creates a number card automatically
4. **Format it**:
   - Click the visual
   - Format pane (paint roller icon)
   - Add title: "Total A/R"
   - Increase font size

#### Metric 2: A/R by Aging Bucket

1. **Click "Stacked bar chart"** in Visualizations (right side)
2. **Drag "Aging Bucket"** to X-axis
3. **Drag "A/R Amount"** to Y-axis
4. **Format colors**:
   - 0-30 days: Green
   - 31-60 days: Yellow
   - 61-90 days: Orange
   - 90+ days: Red

#### Metric 3: Total Revenue

1. **Drag your Revenue column** to canvas
2. Creates a card automatically
3. **Format**: Add title "Total Revenue", format as currency

#### Metric 4: Cash Collections

1. **Drag Payment column** to canvas
2. **Format**: Add title "Cash Collections", format as currency

#### Metric 5: Revenue Trend

1. **Click "Line chart"** in Visualizations
2. **Drag "Date"** to X-axis
3. **Drag "Revenue"** to Y-axis
4. Shows revenue trend over time

### Arrange Your Dashboard:

1. **Resize** visuals by dragging corners
2. **Move** visuals to create a clean layout
3. **Add a title**: Click "Text box" → Type "Therapy Notes Financial Overview"

---

## Step 5: Save Your Report

1. **File** → **Save As**
2. **Name**: "Therapy Notes Financial Dashboard"
3. **Save** to: `C:\PowerBIData\` or a shared network drive

**Congratulations!** You've created your first Power BI dashboard! 🎉

---

## 🎯 Next Steps

### Week 1: Enhance Your Dashboard
- [ ] Add more metrics (Denial Rate, Days in A/R)
- [ ] Format colors and fonts
- [ ] Add filters (date range, payer)
- [ ] Test with more data (last 90 days)

### Week 2: Add Penelope EMR Data
- [ ] Export Penelope reports
- [ ] Import into Power BI
- [ ] Combine with Therapy Notes data
- [ ] Create unified dashboard

### Week 3: Build Additional Dashboards
- [ ] Revenue Cycle Management (RCM) Dashboard
- [ ] Payer Performance Dashboard
- [ ] Accounts Receivable Analysis Dashboard

### Week 4: Automate & Share
- [ ] Set up daily exports from Therapy Notes
- [ ] Refresh Power BI reports daily
- [ ] Share dashboard with finance team (Power BI Pro needed)
- [ ] Get feedback and iterate

---

## 💡 Quick Tips

### Daily Workflow:
1. **Morning (6 AM)**: Export reports from Therapy Notes
2. **Power BI**: Click "Refresh" button
3. **Review**: Check dashboard for any red/yellow alerts
4. **Take Action**: Address any issues identified

### Naming Convention:
- **Files**: `TN_ReportType_YYYY_MM_DD.xlsx`
- **Power BI Report**: Save as `.pbix` file
- **Folder**: `C:\PowerBIData\TherapyNotes\`

### Common Issues:
- **"Data source not found"**: File was moved/renamed → Update path in Power BI
- **Dates showing as text**: Transform Data → Change Type → Date
- **Numbers not calculating**: Transform Data → Change Type → Decimal Number

---

## 📚 Need More Help?

### Detailed Guides:
- **[POWER_BI_SETUP_GUIDE.md](POWER_BI_SETUP_GUIDE.md)** - Complete setup guide
- **[THERAPY_NOTES_PENELOPE_INTEGRATION.md](THERAPY_NOTES_PENELOPE_INTEGRATION.md)** - Integration details
- **[HEALTHCARE_FINANCIAL_KPIs.md](HEALTHCARE_FINANCIAL_KPIs.md)** - KPI definitions

### Power BI Resources:
- **Microsoft Learn**: Free Power BI tutorials
- **Guy in a Cube** (YouTube): Excellent video tutorials
- **Power BI Community**: Ask questions, get answers

---

## ✅ Checklist: First 30 Minutes

- [ ] Downloaded and installed Power BI Desktop
- [ ] Exported 3 key reports from Therapy Notes
- [ ] Saved exports to `C:\PowerBIData\TherapyNotes\`
- [ ] Imported first report (AR Aging) into Power BI
- [ ] Created 5 key metrics on dashboard
- [ ] Arranged and formatted dashboard
- [ ] Saved Power BI report

**Once you complete this checklist, you'll have a working financial dashboard from Therapy Notes!**

---

## 🎓 What You've Learned

After completing this quick start:
- ✅ You know how to export data from Therapy Notes
- ✅ You can import data into Power BI
- ✅ You've created your first financial dashboard
- ✅ You understand the basic workflow

**From here, you can:**
- Expand to include Penelope EMR data
- Add more sophisticated metrics
- Automate the export process
- Share dashboards with your team

---

**Remember**: Start simple, build gradually. Focus on Therapy Notes first since it's your primary system. Once comfortable, add Penelope EMR data and combine them into unified dashboards.

Good luck! 🚀

