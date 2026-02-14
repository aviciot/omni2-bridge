#!/usr/bin/env python3
"""
Configuration Security Validator
================================

This script scans the codebase for:
1. Hardcoded URLs that bypass Traefik
2. Direct OMNI2 access (port 8000)
3. Missing environment variable usage
4. Insecure configuration patterns

Usage: python validate_security_config.py
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple

class SecurityConfigValidator:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues = []
        
        # Patterns to detect security issues
        self.dangerous_patterns = [
            (r'localhost:8000', 'Direct OMNI2 access (bypasses Traefik)'),
            (r'omni2:8000', 'Direct OMNI2 container access (bypasses Traefik)'),
            (r'http://host\.docker\.internal:8000', 'Direct OMNI2 access (bypasses Traefik)'),
            (r'OMNI2_DIRECT_URL', 'Dangerous direct URL configuration'),
            (r'http://[^"\']*:8000', 'Potential direct OMNI2 access'),
        ]
        
        # Hardcoded URL patterns (should use env vars)
        self.hardcoded_patterns = [
            (r'http://host\.docker\.internal:8090', 'Hardcoded Traefik URL (should use env var)'),
            (r'ws://host\.docker\.internal:8090', 'Hardcoded Traefik WebSocket URL (should use env var)'),
        ]
        
        # File extensions to scan
        self.scan_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.env', '.yml', '.yaml', '.md'}
        
        # Directories to skip
        self.skip_dirs = {'.git', '__pycache__', 'node_modules', '.next', 'dist', 'build'}
    
    def scan_file(self, file_path: Path) -> List[Dict]:
        """Scan a single file for security issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
                
                # Check for dangerous patterns
                for pattern, description in self.dangerous_patterns:
                    for line_num, line in enumerate(lines, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            issues.append({
                                'file': str(file_path.relative_to(self.project_root)),
                                'line': line_num,
                                'content': line.strip(),
                                'issue': description,
                                'severity': 'HIGH'
                            })
                
                # Check for hardcoded patterns (lower severity)
                for pattern, description in self.hardcoded_patterns:
                    for line_num, line in enumerate(lines, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            issues.append({
                                'file': str(file_path.relative_to(self.project_root)),
                                'line': line_num,
                                'content': line.strip(),
                                'issue': description,
                                'severity': 'MEDIUM'
                            })
                            
        except Exception as e:
            print(f"[WARNING] Could not scan {file_path}: {e}")
        
        return issues
    
    def scan_directory(self, directory: Path) -> List[Dict]:
        """Recursively scan directory for security issues"""
        all_issues = []
        
        for item in directory.iterdir():
            if item.name.startswith('.') and item.name not in {'.env', '.env.example'}:
                continue
                
            if item.is_dir():
                if item.name not in self.skip_dirs:
                    all_issues.extend(self.scan_directory(item))
            elif item.is_file():
                if item.suffix in self.scan_extensions:
                    all_issues.extend(self.scan_file(item))
        
        return all_issues
    
    def validate_environment_files(self) -> List[Dict]:
        """Validate environment files for proper configuration"""
        issues = []
        
        env_files = [
            self.project_root / '.env',
            self.project_root / 'dashboard' / 'backend' / '.env',
            self.project_root / 'dashboard' / 'frontend' / '.env',
        ]
        
        for env_file in env_files:
            if env_file.exists():
                try:
                    with open(env_file, 'r') as f:
                        content = f.read()
                        
                        # Check for TRAEFIK_BASE_URL
                        if 'dashboard/backend' in str(env_file):
                            if 'TRAEFIK_BASE_URL' not in content:
                                issues.append({
                                    'file': str(env_file.relative_to(self.project_root)),
                                    'line': 0,
                                    'content': '',
                                    'issue': 'Missing TRAEFIK_BASE_URL configuration',
                                    'severity': 'HIGH'
                                })
                        
                        # Check for dangerous direct URLs
                        if ':8000' in content and 'OMNI2_DIRECT_URL' in content:
                            issues.append({
                                'file': str(env_file.relative_to(self.project_root)),
                                'line': 0,
                                'content': '',
                                'issue': 'Contains dangerous OMNI2_DIRECT_URL configuration',
                                'severity': 'HIGH'
                            })
                            
                except Exception as e:
                    print(f"[WARNING] Could not validate {env_file}: {e}")
        
        return issues
    
    def check_docker_compose_security(self) -> List[Dict]:
        """Check Docker Compose files for security issues"""
        issues = []
        
        compose_files = [
            self.project_root / 'docker-compose.yml',
            self.project_root / 'traefik-external' / 'docker-compose.yml',
            self.project_root / 'auth_service' / 'docker-compose.yml',
        ]
        
        for compose_file in compose_files:
            if compose_file.exists():
                try:
                    with open(compose_file, 'r') as f:
                        content = f.read()
                        
                        # Check if OMNI2 ports are exposed
                        if 'omni2' in str(compose_file) and '"8000:8000"' in content:
                            issues.append({
                                'file': str(compose_file.relative_to(self.project_root)),
                                'line': 0,
                                'content': '',
                                'issue': 'OMNI2 port 8000 is exposed (should be internal only)',
                                'severity': 'HIGH'
                            })
                            
                except Exception as e:
                    print(f"[WARNING] Could not check {compose_file}: {e}")
        
        return issues
    
    def run_validation(self):
        """Run complete security validation"""
        print("=" * 60)
        print("SECURITY CONFIGURATION VALIDATOR")
        print("=" * 60)
        print(f"Scanning: {self.project_root}")
        print()
        
        # Scan all files
        print("[INFO] Scanning codebase for security issues...")
        file_issues = self.scan_directory(self.project_root)
        
        # Validate environment files
        print("[INFO] Validating environment files...")
        env_issues = self.validate_environment_files()
        
        # Check Docker Compose security
        print("[INFO] Checking Docker Compose security...")
        docker_issues = self.check_docker_compose_security()
        
        # Combine all issues
        all_issues = file_issues + env_issues + docker_issues
        
        # Group by severity
        high_issues = [i for i in all_issues if i['severity'] == 'HIGH']
        medium_issues = [i for i in all_issues if i['severity'] == 'MEDIUM']
        
        print()
        print("=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)
        
        if not all_issues:
            print("[OK] No security issues found!")
            return True
        
        # Report high severity issues
        if high_issues:
            print(f"[ERROR] {len(high_issues)} HIGH SEVERITY issues found:")
            print()
            for issue in high_issues:
                print(f"  File: {issue['file']}")
                if issue['line'] > 0:
                    print(f"  Line: {issue['line']}")
                    print(f"  Code: {issue['content']}")
                print(f"  Issue: {issue['issue']}")
                print()
        
        # Report medium severity issues
        if medium_issues:
            print(f"[WARNING] {len(medium_issues)} MEDIUM SEVERITY issues found:")
            print()
            for issue in medium_issues:
                print(f"  File: {issue['file']}")
                if issue['line'] > 0:
                    print(f"  Line: {issue['line']}")
                    print(f"  Code: {issue['content']}")
                print(f"  Issue: {issue['issue']}")
                print()
        
        # Summary
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"High severity issues: {len(high_issues)}")
        print(f"Medium severity issues: {len(medium_issues)}")
        print(f"Total issues: {len(all_issues)}")
        
        if high_issues:
            print()
            print("[ERROR] HIGH SEVERITY issues must be fixed before deployment!")
            return False
        elif medium_issues:
            print()
            print("[WARNING] Consider fixing MEDIUM SEVERITY issues for better security.")
            return True
        else:
            print()
            print("[OK] No critical security issues found.")
            return True

def main():
    """Main validation function"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    validator = SecurityConfigValidator(project_root)
    success = validator.run_validation()
    
    if not success:
        exit(1)

if __name__ == "__main__":
    main()