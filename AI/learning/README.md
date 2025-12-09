# AI Learning Module

## Overview

This module processes collected bot data for AI training **BEFORE** data recycling occurs. This ensures your local AI system learns from all collected data before it's cleaned up.

## Data Collection → AI Learning → Data Recycling Flow

1. **Data Collection**: Bots collect browser activity, logs, coordinates, screenshots
2. **AI Learning**: This module extracts and processes all collected data for training
3. **Data Recycling**: Old data is cleaned up after AI has learned from it

## What Gets Processed

- **Browser Activity**: Navigation patterns, element interactions, user flows
- **Bot Logs**: Error patterns, success patterns, workflow insights
- **Coordinate Data**: UI element locations, training coordinates
- **Screenshot Data**: Image recognition training data metadata

## Output

Processed training data is saved to:
```
AI/training_data/
├── browser_activity_YYYYMMDD.json
├── bot_logs_YYYYMMDD.json
├── coordinates_YYYYMMDD.json
├── screenshots_YYYYMMDD.json
└── training_dataset_YYYYMMDD.json (consolidated)
```

## Integration

The AI learning step runs automatically as part of the passive cleanup cycle. No manual intervention needed - it processes data before recycling occurs.

## Customization

To customize what data is extracted or how it's processed, edit `AI/learning/data_processor.py`.

