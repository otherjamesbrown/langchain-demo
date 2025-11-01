"""
Data loading tools for CSV and markdown files.

This module provides LangChain tools for loading and processing
CSV files (company data) and markdown files (research instructions).
These tools can be used by agents to access data during execution.
"""

import os
import csv
from pathlib import Path
from typing import Optional, List, Dict
from langchain_core.tools import tool


@tool
def load_csv_file(file_path: str) -> str:
    """
    Load and return the contents of a CSV file.
    
    This tool reads a CSV file and returns its contents in a formatted
    string that agents can easily parse. Useful for loading company data
    that needs to be researched.
    
    Args:
        file_path: Path to the CSV file (can be relative or absolute)
        
    Returns:
        Formatted string containing CSV data with headers and rows
        
    Example:
        file_path = "examples/companies/sample_companies.csv"
        Returns formatted CSV data with company names and metadata
    """
    try:
        # Resolve path (handles both relative and absolute)
        resolved_path = Path(file_path)
        if not resolved_path.is_absolute():
            # Try relative to project root
            project_root = Path(__file__).parent.parent.parent
            resolved_path = project_root / resolved_path
        
        if not resolved_path.exists():
            return f"Error: File not found at {resolved_path}"
        
        # Read CSV file
        with open(resolved_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        if not rows:
            return "CSV file is empty or has no data rows."
        
        # Get headers
        headers = reader.fieldnames or []
        
        # Format output for agent consumption
        output_lines = []
        output_lines.append(f"CSV File: {resolved_path.name}")
        output_lines.append(f"Total rows: {len(rows)}")
        output_lines.append(f"Headers: {', '.join(headers)}")
        output_lines.append("\nData:")
        
        for i, row in enumerate(rows, 1):
            output_lines.append(f"\nRow {i}:")
            for header in headers:
                value = row.get(header, '')
                output_lines.append(f"  {header}: {value}")
        
        return "\n".join(output_lines)
        
    except Exception as e:
        return f"Error loading CSV file: {str(e)}"


@tool
def load_markdown_file(file_path: str) -> str:
    """
    Load and return the contents of a markdown file.
    
    This tool reads a markdown file (typically containing research
    instructions or guidelines) and returns its contents. Useful for
    loading instructions that guide agent behavior.
    
    Args:
        file_path: Path to the markdown file (can be relative or absolute)
        
    Returns:
        String containing the markdown file contents
        
    Example:
        file_path = "examples/instructions/research_instructions.md"
        Returns the full markdown content with instructions
    """
    try:
        # Resolve path (handles both relative and absolute)
        resolved_path = Path(file_path)
        if not resolved_path.is_absolute():
            # Try relative to project root
            project_root = Path(__file__).parent.parent.parent
            resolved_path = project_root / resolved_path
        
        if not resolved_path.exists():
            return f"Error: File not found at {resolved_path}"
        
        # Read markdown file
        with open(resolved_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            return "Markdown file is empty."
        
        return f"Markdown File: {resolved_path.name}\n\n{content}"
        
    except Exception as e:
        return f"Error loading markdown file: {str(e)}"


@tool
def list_companies_from_csv(file_path: str) -> str:
    """
    Extract company names from a CSV file and return them as a list.
    
    This tool is specifically designed to extract company names from
    CSV files (assuming the first column or a 'company_name' column
    contains company names). Useful for batch processing.
    
    Args:
        file_path: Path to the CSV file containing company data
        
    Returns:
        Comma-separated list of company names
        
    Example:
        file_path = "examples/companies/sample_companies.csv"
        Returns: "Company1, Company2, Company3"
    """
    try:
        # Resolve path
        resolved_path = Path(file_path)
        if not resolved_path.is_absolute():
            project_root = Path(__file__).parent.parent.parent
            resolved_path = project_root / resolved_path
        
        if not resolved_path.exists():
            return f"Error: File not found at {resolved_path}"
        
        # Read CSV and extract company names
        with open(resolved_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            companies = []
            
            # Try to find company name column
            fieldnames = reader.fieldnames or []
            company_column = None
            
            # Look for common company name column names
            for col in ['company_name', 'company', 'name', 'Company Name', 'Company']:
                if col in fieldnames:
                    company_column = col
                    break
            
            # If no specific column found, use first column
            if not company_column and fieldnames:
                company_column = fieldnames[0]
            
            # Extract company names
            for row in reader:
                if company_column and row.get(company_column):
                    companies.append(row[company_column].strip())
        
        if not companies:
            return "No company names found in CSV file."
        
        return ", ".join(companies)
        
    except Exception as e:
        return f"Error extracting companies from CSV: {str(e)}"


# Helper functions (not tools, for direct use in code)

def load_csv_data(file_path: str) -> List[Dict[str, str]]:
    """
    Load CSV data into a list of dictionaries.
    
    This is a direct function (not a LangChain tool) for use in
    application code when you need structured CSV data.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        List of dictionaries, one per row
    """
    resolved_path = Path(file_path)
    if not resolved_path.is_absolute():
        project_root = Path(__file__).parent.parent.parent
        resolved_path = project_root / resolved_path
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_markdown_content(file_path: str) -> str:
    """
    Load markdown file content as a string.
    
    This is a direct function (not a LangChain tool) for use in
    application code when you need markdown content.
    
    Args:
        file_path: Path to markdown file
        
    Returns:
        String content of the file
    """
    resolved_path = Path(file_path)
    if not resolved_path.is_absolute():
        project_root = Path(__file__).parent.parent.parent
        resolved_path = project_root / resolved_path
    
    with open(resolved_path, 'r', encoding='utf-8') as f:
        return f.read()


# List of tools for agent usage
DATA_LOADER_TOOLS = [
    load_csv_file,
    load_markdown_file,
    list_companies_from_csv
]

