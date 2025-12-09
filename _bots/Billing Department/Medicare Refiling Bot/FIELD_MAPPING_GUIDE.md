# PDF Field Mapping Guide

## How Field Mapping Works

The bot uses the `pdf_field_mapping_config` dictionary to determine which PDF fields to fill and which to leave blank.

### Rules:
1. **Fields IN the mapping** → Will be filled with the mapped value
2. **Fields NOT in the mapping** → Will be left blank
3. **Fields mapped to empty string ("")** → Will be left blank (explicitly)
4. **Fields mapped to a client_data key** → Will be filled with data from Excel
5. **Fields mapped to a static value** → Will be filled with that static value
6. **Fields mapped to a lambda function** → Will be filled with the function result

## Currently Configured Fields (Will Be Filled)

### ✅ Beneficiary/Patient Information (from Excel):
- **Beneficiary's Name** → `client_name` (from Excel)
- **Date of Birth** → `dob` (from Excel)
- **MBI** → `patient_member_id` (from Excel)

### ✅ Service Information (from Excel):
- **Date(s) of Service** → `dos` (from Excel)
- **Date of service** → `dos` (alternative field name)
- **Modifier** → `expected_modifier` (from Excel: 93 or 95)

### ✅ Explanation Field (automatically generated):
- **Explain the needed correction below** → Auto-generated explanation text

## Fields That Will Be LEFT BLANK

All other fields NOT listed in the mapping will be left blank, including:
- Provider fields (Provider Name, NPI, PTAN, Tax ID, etc.)
- Checkbox fields (Not our patients, Services Not Rendered, etc.)
- Amount fields (Bill Amount, Billed amount, Overpayment Amount)
- Procedure code fields (Procedure Code(s), Units of service, etc.)
- Signature fields (Printed Name, Telephone Number, Signature, Date Signed)

## How to Add/Remove Fields

### To Fill a Field:
Add it to the `pdf_field_mapping_config` dictionary:

```python
"Field Name": "client_data_key",  # Fill with Excel data
# OR
"Field Name": "Static Value",  # Fill with static value
# OR
"Field Name": lambda client_data: "Custom Logic",  # Fill with function result
```

### To Leave a Field Blank:
1. **Don't include it in the mapping** (recommended - fields not in mapping are automatically left blank)
2. **OR** map it to an empty string: `"Field Name": ""`

### Example: Fill Provider Information

If you want to auto-fill provider information, uncomment and fill these lines:

```python
"Provider Name": "Your Organization Name Here",
"Provider Address": "Your Full Address Here",
"NPI": "Your NPI Number Here",
"PTAN": "Your PTAN Number Here",
"Tax ID": "Your Tax ID Here",
```

### Example: Check a Checkbox

If you need to check a checkbox (e.g., "Services Not Rendered"):

```python
"Services Not Rendered": "Yes",  # or "On" or "1" depending on PDF format
```

## Field Name Matching

The bot automatically handles variations in field names:
- Parentheses: `"(Field Name)"` matches `"Field Name"`
- Escaped characters: `"Date\(s\)"` matches `"Date(s)"`
- Case differences: `"field name"` matches `"Field Name"`

You only need to specify the field name once (with or without parentheses), and the bot will match it to the actual PDF field.

## Testing

After updating the configuration:
1. Run the bot
2. Select your PDF template
3. Click "List PDF Form Fields" to see all available fields
4. Test with one client first to verify fields are filled correctly
5. Check the Activity Log to see which fields were filled and which were skipped

