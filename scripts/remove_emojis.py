#!/usr/bin/env python3
"""
Script to remove all emojis from markdown files in the repository.
This ensures professional, enterprise-appropriate documentation.
"""

import re
import os
from pathlib import Path

def remove_emojis_from_text(text):
    """Remove all emoji characters from text."""
    # Comprehensive emoji pattern that covers most Unicode emoji ranges
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
        "]+", 
        flags=re.UNICODE
    )
    
    # Remove emojis and clean up extra spaces
    text = emoji_pattern.sub('', text)
    
    # Clean up multiple spaces and trailing spaces on lines
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Remove trailing spaces and normalize multiple spaces
        cleaned_line = re.sub(r'\s+', ' ', line.strip())
        cleaned_lines.append(cleaned_line)
    
    return '\n'.join(cleaned_lines)

def process_markdown_file(file_path):
    """Process a single markdown file to remove emojis."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        cleaned_content = remove_emojis_from_text(content)
        
        if cleaned_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"✓ Cleaned emojis from: {file_path}")
            return True
        else:
            print(f"- No emojis found in: {file_path}")
            return False
    except Exception as e:
        print(f"✗ Error processing {file_path}: {e}")
        return False

def main():
    """Main function to process all markdown files."""
    repo_root = Path(__file__).parent.parent
    markdown_files = []
    
    # Find all markdown files
    for pattern in ['*.md', '**/*.md']:
        markdown_files.extend(repo_root.glob(pattern))
    
    # Filter out node_modules and other irrelevant directories
    excluded_dirs = {'node_modules', '.git', '__pycache__', '.pytest_cache', 'workspaces'}
    filtered_files = []
    
    for file_path in markdown_files:
        # Check if file is in excluded directory
        if any(excluded_dir in file_path.parts for excluded_dir in excluded_dirs):
            continue
        filtered_files.append(file_path)
    
    print(f"Found {len(filtered_files)} markdown files to process...")
    
    processed_count = 0
    for file_path in filtered_files:
        if process_markdown_file(file_path):
            processed_count += 1
    
    print(f"\nCompleted! Processed {processed_count} files with emoji removals.")

if __name__ == "__main__":
    main()
