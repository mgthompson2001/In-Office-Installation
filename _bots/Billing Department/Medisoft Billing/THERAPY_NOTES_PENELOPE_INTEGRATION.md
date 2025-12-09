# Therapy Notes & Penelope EMR - Power BI Integration Quick Reference

## 🎯 Overview

This guide provides quick-reference instructions for integrating **Therapy Notes** and **Penelope EMR** data with Power BI for comprehensive financial analysis.

**Your Organization's Systems:**
- **Therapy Notes** - **Primary system**: Data logging, appointment scheduling, billing (focus here first!)
- **Penelope EMR** - Additional EMR functions
- **Medisoft** - Billing and financial reporting (if still in use)

---

## 📊 Therapy Notes Integration

### Quick Setup (Recommended: Manual Export)

**Step 1: Export Reports from Therapy Notes**

1. Log into Therapy Notes web portal
2. Navigate to **Reports** section
3. Export these key reports (to Excel or CSV):

   **Daily Reports:**
   - Accounts Receivable Aging Report
   - Revenue Report (by date range)
   - Payment Report (cash collections)
   
   **Weekly Reports:**
   - Claim Status Report
   - Denial Report (with denial reasons)
   
   **Monthly Reports:**
   - Payer Performance Report
   - Provider Productivity Report

4. Save to folder: `C:\TherapyNotesExports\Daily\` or network share

5. **Naming Convention**: `TN_ReportType_YYYY_MM_DD.xlsx`
   - Example: `TN_ARReport_2024_01_15.xlsx`

**Step 2: Import into Power BI**

1. **Power BI Desktop** → **Get Data** → **Excel** (or **CSV**)
2. Navigate to your export file
3. Select worksheet
4. Click **Load** or **Transform Data** (to clean first)

**Step 3: Standardize Data**

Common transformations needed:
- **Date columns**: Ensure Date format (not Text)
- **Currency columns**: Decimal or Currency format
- **Payer names**: Standardize variations (e.g., "BCBS" → "Blue Cross Blue Shield")
- **Aging buckets**: Create calculated column for 0-30, 31-60, 61-90, 90+

### Advanced: API Integration

**Contact Therapy Notes Support** to:
- Request API access
- Get API credentials (API key)
- Obtain API documentation

**In Power BI:**
- **Get Data** → **Web**
- Enter API endpoint URL
- Configure authentication (API key)
- Load data

**Benefits:**
- ✅ Real-time data
- ✅ Automated refresh
- ✅ No manual exports

**Note**: API access may require additional subscription tier.

### Automated Export (Using Your Existing Bot)

Your **TN Refiling Bot** (`tn_refiling_bot.py`) uses Selenium to automate Therapy Notes. This can be enhanced to:

- Automatically log into Therapy Notes
- Navigate to reports
- Run and export financial reports
- Save to consistent folder format
- Power BI auto-refreshes from folder

**See**: `therapy_notes_powerbi_export.py` (to be created)

---

## 📋 Penelope EMR Integration

### Quick Setup Option 1: Manual Export

**Step 1: Export Reports from Penelope**

1. Log into Penelope EMR
2. Navigate to **Reports** section
3. Export these reports (to Excel or CSV):
   - Financial Summary Report
   - Accounts Receivable Report
   - Payment Report
   - Billing Report (by date range)
   - Service Utilization Report

4. Save to folder: `C:\PenelopeExports\Daily\` or network share

5. **Naming Convention**: `Penelope_ReportType_YYYY_MM_DD.xlsx`

**Step 2: Import into Power BI**

1. **Power BI Desktop** → **Get Data** → **Excel** (or **CSV**)
2. Navigate to export file
3. Select worksheet
4. Click **Load**

### Quick Setup Option 2: Direct Database Connection (Recommended)

**Most Efficient Method** - Penelope typically uses SQL Server or PostgreSQL.

**Step 1: Get Database Connection Details**

Contact your IT team or Penelope support for:
- Database server name
- Database name
- Authentication credentials (Windows or Database)
- Table names containing financial data

**Common Penelope Financial Tables:**
- `billing` or `billing_transactions` - Billing records
- `payments` - Payment records
- `accounts_receivable` or `ar` - A/R data
- `services` - Service records with billing info
- `payers` - Insurance payer information

**Step 2: Connect in Power BI**

1. **Get Data** → **SQL Server** (or **PostgreSQL** if applicable)
2. Enter:
   - Server name
   - Database name
   - Authentication method
3. Select tables or write SQL query
4. Click **Load**

**Example SQL Query for Revenue:**
```sql
SELECT 
    service_date AS ServiceDate,
    SUM(charge_amount) AS Revenue,
    COUNT(*) AS ServiceCount,
    payer_name AS PayerName
FROM billing
WHERE service_date >= DATEADD(month, -12, GETDATE())
GROUP BY service_date, payer_name
ORDER BY service_date DESC
```

**Benefits:**
- ✅ Fastest method
- ✅ Real-time data
- ✅ Automated refresh
- ✅ Can pull exactly what you need

### Advanced: Enhance Your Data Synthesizer

Your **Medisoft Penelope Data Synthesizer** (`medisoft_penelope_data_synthesizer.py`) already works with Penelope data. This can be enhanced to:

- Extract financial data directly from Penelope
- Export to standardized Excel format for Power BI
- Schedule automated exports
- Combine with Medisoft data

**See**: `penelope_powerbi_export.py` (to be created)

---

## 🔗 Combining All Three Systems

### Strategy: Separate Sources, Unified Dashboard

**Approach:** Import each system separately, combine in Power BI

**Step 1: Import Your Active Systems**

1. Import Therapy Notes exports → Table: `TherapyNotes_Revenue` (Priority #1!)
2. Import Penelope exports → Table: `Penelope_Revenue`
3. Import Medisoft exports → Table: `Medisoft_Revenue` (only if still actively used)

**Step 2: Add Source System Identifier**

For each table, add calculated column:
- **Therapy Notes**: `SourceSystem = "Therapy Notes"`
- **Penelope**: `SourceSystem = "Penelope"`
- **Medisoft**: `SourceSystem = "Medisoft"`

**Step 3: Standardize Column Names**

Ensure all three tables have matching column names:
- `ServiceDate` or `Date`
- `Revenue` or `ChargeAmount`
- `PayerName` or `Payer`
- `SourceSystem`

**Step 4: Append Tables**

1. Transform Data → Select first table
2. Home → Append Queries → Select other two tables
3. Power BI combines all rows into one table

**Step 5: Create Unified Measures**

**Total Revenue Across All Systems:**
```DAX
Total Revenue = 
SUM(Combined_Revenue[Revenue])
```

**Revenue by System:**
```DAX
Therapy Notes Revenue = 
CALCULATE(SUM(Combined_Revenue[Revenue]), Combined_Revenue[SourceSystem] = "Therapy Notes")

Penelope Revenue = 
CALCULATE(SUM(Combined_Revenue[Revenue]), Combined_Revenue[SourceSystem] = "Penelope")

Medisoft Revenue = 
CALCULATE(SUM(Combined_Revenue[Revenue]), Combined_Revenue[SourceSystem] = "Medisoft")
```

**Step 6: Build Combined Dashboard**

- Show **Total Revenue** (all systems combined)
- Add **Source System** slicer/filter
- Break down by system with drill-down capability
- Compare performance across systems

---

## 📅 Recommended Export Schedule

### Therapy Notes
- **Frequency**: Daily
- **Time**: 6:00 AM
- **Reports**: AR Aging, Revenue, Payments
- **Method**: Manual export or API if available

### Penelope EMR
- **Frequency**: Daily
- **Time**: 6:00 AM
- **Reports**: Financial Summary, AR, Billing
- **Method**: Database connection (preferred) or manual export

### Medisoft (If Still in Use)
- **Frequency**: Daily (if actively used)
- **Time**: 6:00 AM
- **Reports**: Aging, Payment, Denial, Revenue
- **Method**: Manual export or custom script if needed

**Power BI Refresh Schedule:**
- **Time**: 7:00 AM daily (after all exports complete)
- **Method**: Automated refresh (Power BI Pro) or manual refresh

---

## 🔑 Key Data Fields to Extract

### Common Fields Across All Systems:

| Field Name | Therapy Notes | Penelope | Medisoft | Power BI Use |
|------------|---------------|----------|----------|--------------|
| Service Date | ✓ | ✓ | ✓ | Revenue trends |
| Charge Amount | ✓ | ✓ | ✓ | Revenue calculations |
| Payment Amount | ✓ | ✓ | ✓ | Cash collections |
| Payer Name | ✓ | ✓ | ✓ | Payer analysis |
| Patient ID | ✓ | ✓ | ✓ | Patient matching |
| Claim Status | ✓ | ✓ | ✓ | RCM metrics |
| Aging Days | ✓ | ✓ | ✓ | A/R analysis |
| Denial Reason | ✓ | ✓ | ✓ | Denial management |

### Therapy Notes Specific Fields:
- Appointment Date
- Service Code/CPT Code
- Provider Name
- Clinic Location

### Penelope Specific Fields:
- Penelope ID
- Counselor Name
- Supervisor Name
- Service Type

### Medisoft Specific Fields:
- Chart Number
- Procedure Code
- Insurance Code

---

## 🎯 Recommended Power BI Tables

Create these tables in Power BI to track your financial data:

### 1. Combined_Revenue
**Purpose**: Total revenue across all systems

**Fields:**
- Date (Service Date)
- SourceSystem (Therapy Notes/Penelope/Medisoft)
- Revenue (Charge Amount)
- PayerName
- ProviderName
- Location/Clinic

### 2. Combined_AR
**Purpose**: Accounts Receivable across all systems

**Fields:**
- PatientName
- Date (Service Date)
- SourceSystem
- Balance
- AgingDays
- AgingBucket (0-30, 31-60, 61-90, 90+)
- PayerName

### 3. Combined_Payments
**Purpose**: Payment collections across all systems

**Fields:**
- Date (Payment Date)
- SourceSystem
- PaymentAmount
- PayerName
- PaymentMethod

### 4. Combined_Claims
**Purpose**: Claim status across all systems

**Fields:**
- ClaimID
- Date (Service Date)
- SourceSystem
- Status (Submitted/Paid/Denied)
- DenialReason (if denied)
- PayerName

---

## 💡 Best Practices

### 1. Standardize Payer Names

**Problem**: Same payer may appear differently across systems
- Therapy Notes: "Blue Cross Blue Shield"
- Penelope: "BCBS"
- Medisoft: "BC/BS"

**Solution**: Create a Payer Name mapping table in Power BI

**Steps:**
1. Create new table: `PayerMapping`
2. Columns: `OriginalName`, `StandardizedName`
3. Create relationship to revenue tables
4. Use `StandardizedName` in dashboards

### 2. Handle Date Differences

**Problem**: Systems may have different date formats or time zones

**Solution**: Standardize all dates in Power BI
1. Transform Data → Select date columns
2. Change Type → Date
3. Ensure consistent format across all systems

### 3. Track Data Quality

**Problem**: Missing or incomplete data from one system

**Solution**: Add data quality metrics
1. Create measure: `Missing Data %`
2. Track when each system was last refreshed
3. Add data quality alerts to dashboard

### 4. Performance Optimization

**Problem**: Large datasets from multiple systems slow down Power BI

**Solution**:
1. Import only necessary columns
2. Use date filters to limit historical data
3. Aggregate data when possible (monthly vs. daily)
4. Consider DirectQuery for very large datasets

---

## 🚨 Common Issues & Solutions

### Issue 1: Different Date Formats

**Problem**: Therapy Notes uses MM/DD/YYYY, Penelope uses YYYY-MM-DD

**Solution**:
1. Transform Data → Select date column
2. Change Type → Date
3. Power BI automatically converts format

### Issue 2: Payer Name Variations

**Problem**: Same payer appears differently in each system

**Solution**: Create payer mapping table (see Best Practices #1)

### Issue 3: Missing Data from One System

**Problem**: One system's export is missing or delayed

**Solution**:
1. Add "Last Updated" timestamp to each table
2. Create alert measure: `Days Since Last Update`
3. Show alert on dashboard if > 1 day old

### Issue 4: Duplicate Patients Across Systems

**Problem**: Same patient appears in multiple systems

**Solution**:
1. Add SourceSystem identifier
2. When combining, keep all records (don't deduplicate)
3. Track which system handled which service

---

## ✅ Quick Checklist

### Therapy Notes Setup
- [ ] Identify key reports to export
- [ ] Set up export schedule (daily)
- [ ] Create consistent file naming
- [ ] Test export and import into Power BI
- [ ] Standardize column names and data types
- [ ] Contact Therapy Notes about API access (optional)

### Penelope EMR Setup
- [ ] Contact IT team for database connection details
- [ ] Or set up manual export schedule
- [ ] Create consistent file naming
- [ ] Test connection/import into Power BI
- [ ] Identify which tables contain financial data
- [ ] Test SQL queries for data extraction

### Combined Dashboard Setup
- [ ] Import all three systems' data
- [ ] Add SourceSystem identifier to each
- [ ] Standardize column names across systems
- [ ] Append/combine tables in Power BI
- [ ] Create unified revenue measure
- [ ] Build combined dashboard
- [ ] Add system comparison visuals
- [ ] Test data refresh from all sources

---

## 📞 Getting Help

### Therapy Notes Support
- **Website**: therapynotes.com
- **Support**: Contact through Therapy Notes portal
- **Documentation**: Check Therapy Notes help section
- **API Access**: Request through support

### Penelope EMR Support
- **Website**: aptuitiv.com (Aptuity - Penelope vendor)
- **Support**: Contact through your Penelope implementation
- **Database Access**: Contact IT team or Penelope support
- **Documentation**: Penelope user guide or IT team

### Power BI Support
- **Microsoft Power BI Support**: https://powerbi.microsoft.com/support/
- **Power BI Community**: https://community.powerbi.com/
- **Documentation**: https://docs.microsoft.com/power-bi/

---

## 📚 Additional Resources

- **[POWER_BI_SETUP_GUIDE.md](POWER_BI_SETUP_GUIDE.md)** - Complete Power BI setup guide
- **[HEALTHCARE_FINANCIAL_KPIs.md](HEALTHCARE_FINANCIAL_KPIs.md)** - KPI definitions and benchmarks

---

**Next Steps:**
1. Start with manual exports from Therapy Notes and Penelope
2. Test importing into Power BI
3. Create simple dashboards for each system
4. Then combine into unified dashboard
5. Plan for automation (API or database connections) once comfortable

