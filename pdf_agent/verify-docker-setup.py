#!/usr/bin/env python3
"""
Docker Setup Verification Script
Tests Docker configuration and environment setup
"""

import os
import sys
import subprocess
import json
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"{text}")
    print(f"{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def check_docker_installed():
    """Check if Docker is installed"""
    print_header("1. Checking Docker Installation")
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print_success(f"Docker is installed: {result.stdout.strip()}")
            return True
        else:
            print_error("Docker is not working properly")
            return False
    except FileNotFoundError:
        print_error("Docker is not installed. Please install Docker from https://www.docker.com/")
        return False

def check_docker_compose():
    """Check if Docker Compose is installed"""
    print_header("2. Checking Docker Compose")
    try:
        result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print_success(f"Docker Compose is installed: {result.stdout.strip()}")
            return True
        else:
            print_error("Docker Compose is not working properly")
            return False
    except FileNotFoundError:
        print_error("Docker Compose is not installed. Please install from https://docs.docker.com/compose/install/")
        return False

def check_env_file():
    """Check if .env file exists and has required variables"""
    print_header("3. Checking Environment Configuration")
    
    env_path = Path('.env')
    env_example_path = Path('.env.example')
    
    if not env_example_path.exists():
        print_error(".env.example file not found")
        return False
    
    if not env_path.exists():
        print_warning(".env file not found")
        print("Creating .env from .env.example...")
        with open(env_example_path) as f:
            example_content = f.read()
        with open(env_path, 'w') as f:
            f.write(example_content)
        print_warning("Please update .env with your actual GROQ_API_KEY")
        return False
    
    # Check for GROQ_API_KEY
    with open(env_path) as f:
        env_content = f.read()
    
    if 'GROQ_API_KEY=your_groq_api_key_here' in env_content or 'GROQ_API_KEY=' in env_content:
        if 'GROQ_API_KEY=your_groq_api_key_here' in env_content:
            print_error("GROQ_API_KEY is not set in .env (still has default value)")
            return False
        else:
            # Try to extract the value
            for line in env_content.split('\n'):
                if line.startswith('GROQ_API_KEY='):
                    key_value = line.split('=', 1)[1].strip()
                    if key_value and not key_value.startswith('your_'):
                        print_success("GROQ_API_KEY is configured")
                        return True
            print_error("GROQ_API_KEY appears to be empty")
            return False
    
    print_success(".env file is properly configured")
    return True

def check_docker_files():
    """Check if required Docker files exist"""
    print_header("4. Checking Docker Configuration Files")
    
    required_files = {
        'Dockerfile': 'Main Dockerfile',
        'docker-compose.yml': 'Docker Compose configuration',
        '.dockerignore': 'Docker ignore patterns',
    }
    
    all_present = True
    for filename, description in required_files.items():
        path = Path(filename)
        if path.exists():
            size = path.stat().st_size
            print_success(f"{filename} ({size} bytes) - {description}")
        else:
            print_error(f"{filename} not found - {description}")
            all_present = False
    
    return all_present

def check_requirements():
    """Check if requirements.txt exists"""
    print_header("5. Checking Python Requirements")
    
    req_path = Path('requirements.txt')
    if req_path.exists():
        try:
            # Try different encodings to handle various file formats
            content = None
            for encoding in ['utf-8', 'utf-16', 'latin-1', 'cp1252']:
                try:
                    content = req_path.read_text(encoding=encoding)
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            if content is None:
                print_error("Could not decode requirements.txt with any encoding")
                return False
            
            lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
            print_success(f"requirements.txt found with {len(lines)} dependencies")
            
            # Check for critical dependencies - more robust matching
            critical = ['streamlit', 'chromadb', 'groq', 'sentence-transformers']
            content_lower = content.lower()
            missing = []
            
            for dep in critical:
                # Check if dependency appears as a package name (with == or other version specifiers, or at end of line)
                if not any(dep in line.lower() for line in lines):
                    missing.append(dep)
            
            if missing:
                print_warning(f"Missing critical dependencies: {', '.join(missing)}")
                return False
            
            print_success("All critical dependencies are present")
            return True
        except Exception as e:
            print_error(f"Error checking requirements.txt: {e}")
            return False
    else:
        print_error("requirements.txt not found")
        return False

def check_data_directories():
    """Check if data directories exist or can be created"""
    print_header("6. Checking Data Directories")
    
    directories = [
        'data/uploads',
        'data/chroma_db',
        'data/logs',
    ]
    
    all_ok = True
    for dirname in directories:
        path = Path(dirname)
        if path.exists():
            print_success(f"{dirname} exists")
        else:
            try:
                path.mkdir(parents=True, exist_ok=True)
                print_success(f"{dirname} created")
            except Exception as e:
                print_error(f"Failed to create {dirname}: {e}")
                all_ok = False
    
    return all_ok

def check_docker_daemon():
    """Check if Docker daemon is running"""
    print_header("7. Checking Docker Daemon")
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print_success("Docker daemon is running")
            return True
        else:
            print_error("Docker daemon is not responding")
            return False
    except subprocess.TimeoutExpired:
        print_error("Docker daemon check timed out")
        return False
    except Exception as e:
        print_error(f"Error checking Docker daemon: {e}")
        return False

def summary(checks):
    """Print summary of all checks"""
    print_header("Verification Summary")
    
    passed = sum(checks.values())
    total = len(checks)
    
    for check_name, result in checks.items():
        status = f"{Colors.GREEN}✓ PASS{Colors.END}" if result else f"{Colors.RED}✗ FAIL{Colors.END}"
        print(f"{status} - {check_name}")
    
    print(f"\n{Colors.BLUE}Result: {passed}/{total} checks passed{Colors.END}\n")
    
    if passed == total:
        print_success("All checks passed! You're ready to deploy.")
        print(f"\n{Colors.BLUE}Next steps:{Colors.END}")
        print("  1. Review your .env file")
        print("  2. Run: docker-compose up -d")
        print("  3. Access the app at: http://localhost:8501")
        return 0
    else:
        print_error(f"Please fix {total - passed} check(s) before deploying.")
        return 1

def main():
    print(f"\n{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════╗")
    print("║      PDF Agent Docker Setup Verification Tool          ║")
    print("╚════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    checks = {
        "Docker Installation": check_docker_installed(),
        "Docker Compose": check_docker_compose(),
        "Environment Configuration": check_env_file(),
        "Docker Configuration Files": check_docker_files(),
        "Python Requirements": check_requirements(),
        "Data Directories": check_data_directories(),
        "Docker Daemon": check_docker_daemon(),
    }
    
    exit_code = summary(checks)
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
