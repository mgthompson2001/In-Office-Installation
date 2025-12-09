#!/usr/bin/env python3
"""
AI Learning Data Processor - Extracts and processes collected data for AI training
This runs BEFORE data recycling to ensure AI learns from all collected data.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

_LOGGER = logging.getLogger("ai_learning")


class AIDataProcessor:
    """Processes collected bot data for AI training before recycling."""
    
    def __init__(self, installation_dir: Path):
        self.installation_dir = Path(installation_dir)
        self.training_data_dir = self.installation_dir / "AI" / "training_data"
        self.training_data_dir.mkdir(parents=True, exist_ok=True)
    
    def process_all_data(self) -> Dict[str, Any]:
        """Process all collected data for AI training.
        
        Returns:
            Dictionary with processing statistics
        """
        _LOGGER.info("Starting AI data processing from collected bot data...")
        
        stats = {
            'browser_activity_records': 0,
            'bot_logs_processed': 0,
            'coordinate_data_extracted': 0,
            'screenshot_data_extracted': 0,
            'training_files_created': 0
        }
        
        # Process browser activity databases
        stats['browser_activity_records'] = self._process_browser_activity()
        
        # Process bot logs
        stats['bot_logs_processed'] = self._process_bot_logs()
        
        # Process coordinate training data
        stats['coordinate_data_extracted'] = self._process_coordinate_data()
        
        # Process screenshot/image data
        stats['screenshot_data_extracted'] = self._process_screenshot_data()
        
        # Create consolidated training dataset
        stats['training_files_created'] = self._create_training_dataset()
        
        _LOGGER.info(f"AI data processing complete: {stats}")
        return stats
    
    def _process_browser_activity(self) -> int:
        """Extract browser activity data for AI training."""
        records_processed = 0
        
        try:
            # Find all browser activity databases
            secure_dirs = list(self.installation_dir.rglob("_secure_data"))
            
            all_navigations = []
            all_interactions = []
            
            for secure_dir in secure_dirs:
                db_path = secure_dir / "browser_activity.db"
                if not db_path.exists():
                    continue
                
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # Extract page navigations
                    cursor.execute("SELECT * FROM page_navigations")
                    nav_rows = cursor.fetchall()
                    for row in nav_rows:
                        all_navigations.append({
                            'session_id': row[1],
                            'timestamp': row[2],
                            'page_title': row[3],
                            'url': row[4],
                            'anonymized_url': row[5]
                        })
                    
                    # Extract element interactions
                    cursor.execute("SELECT * FROM element_interactions")
                    elem_rows = cursor.fetchall()
                    for row in elem_rows:
                        all_interactions.append({
                            'session_id': row[1],
                            'timestamp': row[2],
                            'action_type': row[3],
                            'element_tag': row[4],
                            'element_id': row[5],
                            'element_name': row[6],
                            'element_type': row[7],
                            'element_value': row[8],
                            'anonymized_url': row[9]
                        })
                    
                    conn.close()
                    records_processed += len(nav_rows) + len(elem_rows)
                    
                except Exception as e:
                    _LOGGER.warning(f"Error processing browser activity from {db_path}: {e}")
            
            # Save processed data
            if all_navigations or all_interactions:
                output_file = self.training_data_dir / f"browser_activity_{datetime.now().strftime('%Y%m%d')}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'navigations': all_navigations,
                        'interactions': all_interactions,
                        'processed_at': datetime.now().isoformat()
                    }, f, indent=2)
                _LOGGER.info(f"Saved {len(all_navigations)} navigations and {len(all_interactions)} interactions to {output_file}")
            
        except Exception as e:
            _LOGGER.warning(f"Error during browser activity processing: {e}")
        
        return records_processed
    
    def _process_bot_logs(self) -> int:
        """Extract patterns and insights from bot logs."""
        logs_processed = 0
        
        try:
            # Find all log files
            log_files = list(self.installation_dir.rglob("*.log"))
            
            all_log_entries = []
            
            for log_file in log_files:
                # Skip old logs and protected directories
                if any(skip in str(log_file) for skip in ['Past Logs', 'Example Log', 'Cursor versions', '__pycache__']):
                    continue
                
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        for line in lines:
                            # Extract structured log data
                            if 'ERROR' in line or 'WARNING' in line or 'INFO' in line:
                                all_log_entries.append({
                                    'log_file': str(log_file.relative_to(self.installation_dir)),
                                    'entry': line.strip(),
                                    'timestamp': self._extract_timestamp(line)
                                })
                                logs_processed += 1
                except Exception as e:
                    _LOGGER.debug(f"Could not process log file {log_file}: {e}")
            
            # Save processed log data
            if all_log_entries:
                output_file = self.training_data_dir / f"bot_logs_{datetime.now().strftime('%Y%m%d')}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'log_entries': all_log_entries,
                        'processed_at': datetime.now().isoformat()
                    }, f, indent=2)
                _LOGGER.info(f"Processed {logs_processed} log entries from {len(log_files)} log files")
            
        except Exception as e:
            _LOGGER.warning(f"Error during log processing: {e}")
        
        return logs_processed
    
    def _process_coordinate_data(self) -> int:
        """Extract coordinate training data."""
        coordinates_extracted = 0
        
        try:
            # Find all coordinate JSON files
            coord_files = list(self.installation_dir.rglob("*_coordinates.json"))
            coord_files.extend(list(self.installation_dir.rglob("*coordinates*.json")))
            
            all_coordinates = []
            
            for coord_file in coord_files:
                try:
                    with open(coord_file, 'r', encoding='utf-8') as f:
                        coords_data = json.load(f)
                        if isinstance(coords_data, dict):
                            for element_name, coord_info in coords_data.items():
                                all_coordinates.append({
                                    'bot': str(coord_file.parent.name),
                                    'element_name': element_name,
                                    'coordinates': coord_info,
                                    'source_file': str(coord_file.relative_to(self.installation_dir))
                                })
                                coordinates_extracted += 1
                except Exception as e:
                    _LOGGER.debug(f"Could not process coordinate file {coord_file}: {e}")
            
            # Save coordinate data
            if all_coordinates:
                output_file = self.training_data_dir / f"coordinates_{datetime.now().strftime('%Y%m%d')}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'coordinates': all_coordinates,
                        'processed_at': datetime.now().isoformat()
                    }, f, indent=2)
                _LOGGER.info(f"Extracted {coordinates_extracted} coordinate mappings")
            
        except Exception as e:
            _LOGGER.warning(f"Error during coordinate processing: {e}")
        
        return coordinates_extracted
    
    def _process_screenshot_data(self) -> int:
        """Extract screenshot/image training data metadata."""
        screenshots_processed = 0
        
        try:
            # Find all screenshot/image files used for training
            image_extensions = ['.png', '.jpg', '.jpeg']
            all_screenshots = []
            
            for ext in image_extensions:
                for img_file in self.installation_dir.rglob(f"*{ext}"):
                    # Skip if in protected directories
                    if any(skip in str(img_file) for skip in ['__pycache__', '.git', 'Cursor versions']):
                        continue
                    
                    try:
                        # Get file metadata
                        stat = img_file.stat()
                        all_screenshots.append({
                            'filename': img_file.name,
                            'path': str(img_file.relative_to(self.installation_dir)),
                            'size_bytes': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'bot': str(img_file.parent.name)
                        })
                        screenshots_processed += 1
                    except Exception as e:
                        _LOGGER.debug(f"Could not process screenshot {img_file}: {e}")
            
            # Save screenshot metadata
            if all_screenshots:
                output_file = self.training_data_dir / f"screenshots_{datetime.now().strftime('%Y%m%d')}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'screenshots': all_screenshots,
                        'processed_at': datetime.now().isoformat()
                    }, f, indent=2)
                _LOGGER.info(f"Processed metadata for {screenshots_processed} screenshots")
            
        except Exception as e:
            _LOGGER.warning(f"Error during screenshot processing: {e}")
        
        return screenshots_processed
    
    def _create_training_dataset(self) -> int:
        """Create consolidated training dataset for AI."""
        try:
            # Load all processed data files
            training_files = list(self.training_data_dir.glob("*.json"))
            
            consolidated = {
                'dataset_version': '1.0',
                'created_at': datetime.now().isoformat(),
                'installation_dir': str(self.installation_dir),
                'data_sources': []
            }
            
            for training_file in training_files:
                try:
                    with open(training_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        consolidated['data_sources'].append({
                            'file': training_file.name,
                            'type': training_file.stem.split('_')[0],
                            'record_count': len(data.get('navigations', [])) + 
                                          len(data.get('interactions', [])) +
                                          len(data.get('log_entries', [])) +
                                          len(data.get('coordinates', [])) +
                                          len(data.get('screenshots', []))
                        })
                except Exception as e:
                    _LOGGER.debug(f"Could not include {training_file} in consolidated dataset: {e}")
            
            # Save consolidated dataset
            consolidated_file = self.training_data_dir / f"training_dataset_{datetime.now().strftime('%Y%m%d')}.json"
            with open(consolidated_file, 'w', encoding='utf-8') as f:
                json.dump(consolidated, f, indent=2)
            
            _LOGGER.info(f"Created consolidated training dataset: {consolidated_file}")
            return len(training_files)
            
        except Exception as e:
            _LOGGER.warning(f"Error creating training dataset: {e}")
            return 0
    
    def _extract_timestamp(self, log_line: str) -> Optional[str]:
        """Extract timestamp from log line."""
        try:
            # Try to extract ISO format timestamp
            import re
            match = re.search(r'\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}', log_line)
            if match:
                return match.group(0)
        except Exception:
            pass
        return None


def process_data_for_ai(installation_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Main entry point to process all data for AI training.
    
    Args:
        installation_dir: Path to installation root. If None, auto-detects.
        
    Returns:
        Dictionary with processing statistics
    """
    if installation_dir is None:
        # Auto-detect from AI folder location
        current_file = Path(__file__).resolve()
        if current_file.parent.name == "learning" and current_file.parent.parent.name == "AI":
            installation_dir = current_file.parent.parent.parent
        else:
            installation_dir = current_file.parent.parent.parent
    
    processor = AIDataProcessor(Path(installation_dir))
    return processor.process_all_data()

