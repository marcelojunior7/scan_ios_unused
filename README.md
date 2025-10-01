# iOS Unused Scanner

A simple Python CLI tool to detect **unused assets** (`.xcassets`) and **unused Swift files** in iOS projects.  
Useful for cleaning up large projects, reducing app size, and improving maintainability.

## Features
- Scans `.xcassets` catalogs and finds assets **not referenced** in:
  - Swift code (`Image("...")`, `UIImage(named:)`, `Color("...")`, `UIColor(named:)`)
  - Storyboards / XIBs
  - `Info.plist` (App Icons, Launch Screen)
- Detects Swift files whose declared types are **never referenced** in other files (heuristic).

## Requirements
- Python **3.8+**
- Works on macOS and Linux (tested with iOS projects).

## Installation
Clone or copy the script into your project or into a separate tools folder.

```bash
git clone https://github.com/yourusername/ios-unused-scanner.git
cd ios-unused-scanner
```

This will generate two files inside the Reports/ folder:
	•	unused_assets.txt
	•	unused_swift_files.txt

## Usage Examples

Basic usage

```bash
python3 scan_ios_unused.py --path /Users/you/Projects/MyApp --output-dir Reports
```
Protect common assets
```bash
python3 scan_ios_unused.py --protect AppIcon AccentColor LaunchScreen
```

## Output Examples

unused_assets.txt
```
/Users/you/Projects/MyApp/Assets.xcassets/OldLogo.imageset
/Users/you/Projects/MyApp/Assets.xcassets/UnusedIcon.imageset
```
unused_swift_files.txt
```
/Users/you/Projects/MyApp/Modules/Legacy/OldViewController.swift
/Users/you/Projects/MyApp/Helpers/UnusedHelper.swift
```

## Notes & Limitations
### Swift unused detection is heuristic:
- Reflection, @objc selectors, SwiftUI previews, and dependency injection may cause false positives.
- Use --keep or --keep-regex to exclude those cases.
### Assets:
- Dynamic references (e.g., UIImage(named: someVariable)) will not be detected.
- Static string references work reliably.
- Safe to use for reporting. Always review before deleting files.
