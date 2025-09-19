#!/usr/bin/env python3
"""
Reward Groups Reporter - Fixed Version
======================================

This script fetches ALL reward group data from the Kognitiv Loyalty API
with proper pagination and enrichment, generating a comprehensive markdown report.

Key Features:
- Fetches all reward groups with complete pagination
- Enriches each reward group with detailed metadata
- Interprets rules using rule definitions
- Generates comprehensive markdown for LLM integration

Usage:
    python reward_groups_reporter_fixed.py --token YOUR_JWT_TOKEN

Requirements:
    - requests library (pip install requests)
    - Valid JWT token for the Kognitiv Loyalty API
"""

import json
import requests
import argparse
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

class RewardGroupsReporterFixed:
    def __init__(self, token: str, base_url: str = "https://ca.kognitivloyalty.com/api"):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "api-version": "2025.3",
            "Content-Type": "application/json"
        }
        self.rule_definitions = None
        
    def make_api_call(self, endpoint: str) -> Dict[str, Any]:
        """Make an API call and return the JSON response."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making API call to {endpoint}: {e}")
            return {}
    
    def fetch_all_reward_groups(self, per_page: int = 100) -> List[Dict[str, Any]]:
        """Fetch all reward groups with complete pagination."""
        print("Fetching all reward groups with pagination...")
        all_groups = []
        page = 1
        max_pages = 20  # Safety limit
        
        while page <= max_pages:
            # Check if the API supports pagination parameters
            endpoint = f"groups/reward?page={page}&perPage={per_page}"
            print(f"Fetching page {page}...")
            
            response = self.make_api_call(endpoint)
            
            # Check if API call failed
            if not response:
                print(f"API call failed for page {page}")
                # Try without pagination parameters (fallback)
                if page == 1:
                    print("Trying without pagination parameters...")
                    response = self.make_api_call("groups/reward")
                    if response:
                        groups_data = response.get("data", [])
                        print(f"Fetched {len(groups_data)} reward groups (no pagination)")
                        return groups_data
                break
                
            groups_data = response.get("data", [])
            meta_data = response.get("meta", {})
            
            print(f"Page {page}: Found {len(groups_data)} reward groups")
            if meta_data:
                print(f"Meta data: {meta_data}")
            
            # If no groups found, we've reached the end
            if not groups_data or len(groups_data) == 0:
                print(f"No reward groups found on page {page} - reached end of data")
                break
                
            # Add groups to our collection
            all_groups.extend(groups_data)
            print(f"Total reward groups so far: {len(all_groups)}")
            
            # If we got fewer groups than requested per page, we've reached the end
            if len(groups_data) < per_page:
                print(f"Got {len(groups_data)} groups (less than {per_page}) - reached end of pagination")
                break
                
            page += 1
            time.sleep(0.2)  # Delay to be respectful to the API
        
        if page > max_pages:
            print(f"Warning: Reached maximum page limit ({max_pages}). There might be more reward groups.")
        
        print(f"✅ PAGINATION COMPLETE: Total reward groups fetched: {len(all_groups)}")
        
        # Remove duplicates based on id
        unique_groups = []
        seen_ids = set()
        for group in all_groups:
            group_id = group.get("id")
            if group_id not in seen_ids:
                seen_ids.add(group_id)
                unique_groups.append(group)
        
        if len(unique_groups) != len(all_groups):
            print(f"Removed {len(all_groups) - len(unique_groups)} duplicate reward groups")
        
        print(f"✅ FINAL COUNT: {len(unique_groups)} unique reward groups")
        return unique_groups
    
    def fetch_reward_group_details(self, group_id: int) -> Dict[str, Any]:
        """Fetch detailed information for a specific reward group."""
        print(f"Fetching details for reward group {group_id}...")
        response = self.make_api_call(f"groups/reward/{group_id}")
        return response.get("data", {})
    
    def merge_reward_group_data(self, listing_data: Dict[str, Any], detail_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge data from listing call and detail call, preserving all information."""
        merged = {}
        
        # Start with listing data
        merged.update(listing_data)
        
        # Add detail data, but don't overwrite listing data unless it's None
        for key, value in detail_data.items():
            if key not in merged or merged[key] is None:
                merged[key] = value
            elif key == "statistics" and value is not None:
                # Merge statistics if both exist
                if merged.get("statistics"):
                    merged["statistics"].update(value)
                else:
                    merged["statistics"] = value
        
        return merged
    
    def fetch_rule_definitions(self) -> Dict[str, Any]:
        """Fetch all rule definitions for interpretation."""
        if self.rule_definitions is None:
            print("Fetching rule definitions...")
            self.rule_definitions = self.make_api_call("groups/ruleDefinitions")
        return self.rule_definitions
    
    def get_rule_definition(self, rule_def_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific rule definition by ID."""
        rule_defs = self.fetch_rule_definitions()
        for rule_def in rule_defs.get("data", []):
            if rule_def["id"] == rule_def_id:
                return rule_def
        return None
    
    def get_component_definition(self, rule_def: Dict[str, Any], comp_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific component definition from a rule definition."""
        if rule_def:
            for component in rule_def.get("components", []):
                if component["id"] == comp_id:
                    return component
        return None
    
    def format_date(self, date_str: str) -> str:
        """Format a date string for human readability."""
        if not date_str:
            return "Not specified"
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%B %d, %Y at %H:%M UTC")
        except:
            return date_str
    
    def interpret_operator(self, operator: str) -> str:
        """Convert API operators to human-readable text."""
        operator_map = {
            "isEqual": "equals",
            "isNotEqual": "does not equal",
            "isGreaterThan": "is greater than",
            "isLessThan": "is less than",
            "isGreaterThanOrEqualTo": "is greater than or equal to",
            "isLessThanOrEqualTo": "is less than or equal to",
            "isBetween": "is between",
            "isNotBetween": "is not between",
            "contains": "contains",
            "doesNotContain": "does not contain"
        }
        return operator_map.get(operator, operator)
    
    def interpret_rule_value(self, value_item: Dict[str, Any], rule_def: Dict[str, Any]) -> str:
        """Interpret a rule value item into human-readable text."""
        try:
            component = value_item.get("component", {})
            component_id = component.get("id")
            component_type = component.get("type")
            operator = value_item.get("operator", "")
            value1 = value_item.get("value1")
            value2 = value_item.get("value2")
            selected_text = value_item.get("selectedText")
            
            # Get component definition for name
            component_def = self.get_component_definition(rule_def, component_id)
            component_name = component_def.get("name", "Unknown Component") if component_def else "Unknown Component"
            
            operator_text = self.interpret_operator(operator)
            
            # Handle different component types and operators - focus on meaningful information
            if component_type == "dropdown" and selected_text:
                # For dropdowns, the selected text is what matters most
                return f"{selected_text}"
            elif component_type == "dateRange":
                if operator == "customDates" and value1 and value2:
                    return f"Date Range: {value1} to {value2}"
                elif operator == "previous365Days":
                    return f"Date Range: Previous 365 Days"
                elif operator == "previousMonth":
                    return f"Date Range: Previous Month"
                elif value1 and value2:
                    return f"Date Range: {value1} to {value2}"
                elif value1:
                    return f"Date Range: from {value1}"
                else:
                    return f"Date Range: not specified"
            elif selected_text:
                # If there's selected text, use it regardless of component type
                return f"{selected_text}"
            elif value1 and value2:
                return f"{value1} to {value2}"
            elif value1:
                return f"{value1}"
            else:
                return f"(no value specified)"
        except Exception as e:
            # Fallback for any parsing errors
            return f"Rule value interpretation error: {str(e)}"
    
    def interpret_rule(self, rule: Dict[str, Any]) -> str:
        """Interpret a complete rule into human-readable text."""
        rule_def_id = rule.get("ruleDefinition", {}).get("id")
        if not rule_def_id:
            return "Rule definition not found"
        
        rule_def = self.get_rule_definition(rule_def_id)
        if not rule_def:
            return f"Rule definition {rule_def_id} not found"
        
        rule_name = rule_def.get("name", f"Rule {rule_def_id}")
        
        # Handle the new structure with 'values' array
        values = rule.get("values", [])
        if values:
            value_texts = []
            for value_item in values:
                value_text = self.interpret_rule_value(value_item, rule_def)
                if value_text:  # Only add non-empty strings
                    value_texts.append(value_text)
            
            if len(value_texts) == 1:
                return f"{rule_name}: {value_texts[0]}"
            elif len(value_texts) > 1:
                # Join multiple values with AND (they're typically all required)
                values_joined = " AND ".join(value_texts)
                return f"{rule_name}: {values_joined}"
            else:
                return f"{rule_name}: (no interpretable values)"
        
        # Fallback to old structure with 'conditions' array (if it exists)
        conditions = rule.get("conditions", [])
        if conditions:
            condition_texts = []
            for condition in conditions:
                # This would need the old interpret_rule_condition method
                condition_texts.append(f"Condition: {condition}")
            
            logic = rule.get("logic", "and").upper()
            
            if len(condition_texts) == 1:
                return f"{rule_name}: {condition_texts[0]}"
            else:
                conditions_joined = f" {logic} ".join(condition_texts)
                return f"{rule_name}: {conditions_joined}"
        
        # If no values or conditions, just return rule name
        return rule_name
    
    def generate_reward_groups_summary(self, groups_with_details: List[Dict[str, Any]]) -> str:
        """Generate summary table for all reward groups."""
        lines = [
            "## Reward Groups Summary",
            "",
            "| ID | Name | Status | Rebuild Frequency | Member Count | Rules Count | Last Updated |",
            "|----|------|--------|-------------------|--------------|-------------|--------------|"
        ]
        
        for group in sorted(groups_with_details, key=lambda x: int(x.get("id", 0))):
            group_id = group.get("id", "N/A")
            name = group.get("name", "Unnamed")
            status = group.get("status", "Unknown")
            rebuild_freq = group.get("rebuildFrequency", "Unknown")
            
            # Get member count from statistics
            member_count = "N/A"
            if group.get("statistics") and group["statistics"].get("memberCount") is not None:
                member_count = f"{group['statistics']['memberCount']:,}"
            
            # Count rules
            rules_count = len(group.get("rules", []))
            
            # Get last updated
            last_updated = "N/A"
            if group.get("lastUpdated"):
                last_updated = self.format_date(group["lastUpdated"])
            
            lines.append(
                f"| {group_id} | {name} | {status} | {rebuild_freq} | {member_count} | {rules_count} | {last_updated} |"
            )
        
        return "\n".join(lines)
    
    def generate_detailed_reward_groups(self, groups_with_details: List[Dict[str, Any]]) -> str:
        """Generate detailed sections for each reward group."""
        lines = [
            "## Detailed Reward Group Information",
            "",
            "*Note: All data from both listing calls and detailed meta calls is preserved.*",
            ""
        ]
        
        for group in sorted(groups_with_details, key=lambda x: int(x.get("id", 0))):
            lines.append(f"### {group.get('name', 'Unnamed Group')} (ID: {group.get('id', 'N/A')})")
            lines.append("")
            
            # Basic Information
            lines.append(f"**Status:** {group.get('status', 'Unknown')}")
            lines.append(f"**Rebuild Frequency:** {group.get('rebuildFrequency', 'Unknown')}")
            
            if group.get("description"):
                lines.append(f"**Description:** {group['description']}")
            
            # Timestamps
            if group.get("createdAt"):
                lines.append(f"**Created:** {self.format_date(group['createdAt'])}")
            
            if group.get("lastUpdated"):
                lines.append(f"**Last Updated:** {self.format_date(group['lastUpdated'])}")
            
            if group.get("lastRebuilt"):
                lines.append(f"**Last Rebuilt:** {self.format_date(group['lastRebuilt'])}")
            
            # Statistics
            if group.get("statistics"):
                lines.append("")
                lines.append("**Statistics:**")
                stats = group["statistics"]
                for key, value in stats.items():
                    if value is not None:
                        if isinstance(value, (int, float)):
                            lines.append(f"- {key.replace('_', ' ').title()}: {value:,}")
                        else:
                            lines.append(f"- {key.replace('_', ' ').title()}: {value}")
            
            # Parent Group
            if group.get("parentGroup"):
                lines.append("")
                lines.append("**Parent Group:**")
                parent = group["parentGroup"]
                lines.append(f"- ID: {parent.get('id')}")
                if parent.get("name"):
                    lines.append(f"- Name: {parent['name']}")
            
            # Rules
            rules = group.get("rules", [])
            if rules:
                lines.append("")
                lines.append("**Rules:**")
                lines.append("")
                
                for i, rule in enumerate(rules, 1):
                    rule_interpretation = self.interpret_rule(rule)
                    lines.append(f"**Rule {i}:** {rule_interpretation}")
                    lines.append("")
                
                # Logic between rules
                logic = group.get("logic", "any")
                if len(rules) > 1:
                    lines.append(f"**Rule Logic:** Member qualifies if they match **{logic.upper()}** of the above rules")
                    lines.append("")
            
            # Additional fields
            additional_fields = ["isValid", "isActive", "allowDuplicates", "maxMembers"]
            additional_info = []
            
            for field in additional_fields:
                if group.get(field) is not None:
                    value = group[field]
                    if isinstance(value, bool):
                        additional_info.append(f"- {field.replace('_', ' ').title()}: {'Yes' if value else 'No'}")
                    else:
                        additional_info.append(f"- {field.replace('_', ' ').title()}: {value:,}" if isinstance(value, (int, float)) else f"- {field.replace('_', ' ').title()}: {value}")
            
            if additional_info:
                lines.append("")
                lines.append("**Additional Information:**")
                lines.extend(additional_info)
            
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_statistics_summary(self, groups_with_details: List[Dict[str, Any]]) -> str:
        """Generate overall statistics summary."""
        total_groups = len(groups_with_details)
        
        # Count by status
        status_counts = {}
        for group in groups_with_details:
            status = group.get("status", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by rebuild frequency
        frequency_counts = {}
        for group in groups_with_details:
            frequency = group.get("rebuildFrequency", "Unknown")
            frequency_counts[frequency] = frequency_counts.get(frequency, 0) + 1
        
        # Calculate total members
        total_members = 0
        groups_with_member_count = 0
        for group in groups_with_details:
            if group.get("statistics") and group["statistics"].get("memberCount") is not None:
                total_members += group["statistics"]["memberCount"]
                groups_with_member_count += 1
        
        lines = [
            "## Statistics Summary",
            "",
            f"**Total Reward Groups:** {total_groups}",
            f"**Total Members Across All Groups:** {total_members:,}",
            f"**Groups with Member Count Data:** {groups_with_member_count}",
            "",
            "**Groups by Status:**"
        ]
        
        for status, count in sorted(status_counts.items()):
            lines.append(f"- {status}: {count}")
        
        lines.append("")
        lines.append("**Groups by Rebuild Frequency:**")
        for frequency, count in sorted(frequency_counts.items()):
            lines.append(f"- {frequency}: {count}")
        
        lines.append("")
        return "\n".join(lines)
    
    def generate_reward_group_report(self, output_file: str = "reward_groups_complete_report.md") -> str:
        """Generate the complete reward groups report."""
        print("Starting complete reward groups report generation...")
        
        # Fetch all reward groups with complete pagination
        groups_listing = self.fetch_all_reward_groups()
        if not groups_listing:
            print("No reward groups found or API call failed.")
            return ""
        
        print(f"Found {len(groups_listing)} reward groups")
        
        # Fetch detailed information for each reward group and merge with listing data
        print(f"\n🔄 Starting enrichment process for {len(groups_listing)} reward groups...")
        groups_with_details = []
        successful_fetches = 0
        failed_fetches = 0
        skipped_groups = 0
        
        for i, listing_group in enumerate(groups_listing, 1):
            group_id = listing_group.get("id")
            
            print(f"Processing {i}/{len(groups_listing)}: Group ID {group_id} - {listing_group.get('name', 'Unnamed')}")
            
            if group_id:
                detail_data = self.fetch_reward_group_details(group_id)
                if detail_data:
                    # Merge listing and detail data
                    merged_group = self.merge_reward_group_data(listing_group, detail_data)
                    groups_with_details.append(merged_group)
                    successful_fetches += 1
                    print(f"  ✅ Successfully enriched")
                else:
                    # If detail fetch fails, still include listing data
                    groups_with_details.append(listing_group)
                    failed_fetches += 1
                    print(f"  ⚠️ Failed to fetch details, using listing data only")
            else:
                print(f"  ❌ Skipping - missing group ID")
                skipped_groups += 1
                    
            time.sleep(0.1)  # Small delay to be respectful to the API
        
        print(f"\n📊 ENRICHMENT SUMMARY:")
        print(f"  ✅ Successfully enriched: {successful_fetches}")
        print(f"  ⚠️ Listing data only: {failed_fetches}")
        print(f"  ❌ Skipped: {skipped_groups}")
        print(f"  📋 Total processed: {len(groups_with_details)}")
        
        # Fetch supporting data
        self.fetch_rule_definitions()
        
        # Generate the report
        report_lines = [
            "# Complete Reward Groups Report",
            "",
            f"**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}",
            f"**Total Reward Groups:** {len(groups_with_details)}",
            f"**Successfully Enriched:** {successful_fetches}",
            f"**Listing Data Only:** {failed_fetches}",
            "",
            "*This report contains complete reward group information with rule interpretations.*",
            "*All data from both listing calls and detailed meta calls is preserved.*",
            ""
        ]
        
        # Add statistics summary
        report_lines.append(self.generate_statistics_summary(groups_with_details))
        
        # Add reward groups summary
        report_lines.append(self.generate_reward_groups_summary(groups_with_details))
        report_lines.append("")
        
        # Add detailed sections
        report_lines.append(self.generate_detailed_reward_groups(groups_with_details))
        
        # Write to file
        report_content = "\n".join(report_lines)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        print(f"Complete report generated successfully: {output_file}")
        return report_content



"""
Tiers Reporter
==============

This script fetches tier sets data from the Kognitiv Loyalty API
and generates a comprehensive markdown report with human-readable interpretations.

Usage:
    python tiers_reporter.py --token YOUR_JWT_TOKEN

Requirements:
    - requests library (pip install requests)
    - Valid JWT token for the Kognitiv Loyalty API
"""

import json
import requests
import argparse
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

class TiersReporter:
    def __init__(self, token: str, base_url: str = "https://ca.kognitivloyalty.com/api"):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "api-version": "2025.3",
            "Content-Type": "application/json"
        }
        self.tier_rules_cache = None
        self.clubs_cache = None
        
    def make_api_call(self, endpoint: str) -> Dict[str, Any]:
        """Make an API call and return the JSON response."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making API call to {endpoint}: {e}")
            return {}
    
    def fetch_tier_sets(self) -> List[Dict[str, Any]]:
        """Fetch the list of all tier sets."""
        print("Fetching tier sets list...")
        response = self.make_api_call("tierSets/")
        return response.get("data", [])
    
    def fetch_tier_set_details(self, tier_set_id: int) -> Dict[str, Any]:
        """Fetch detailed information for a specific tier set."""
        print(f"Fetching details for tier set {tier_set_id}...")
        response = self.make_api_call(f"tierSets/{tier_set_id}")
        return response.get("data", {})
    
    def fetch_tier_rules(self) -> Dict[str, Any]:
        """Fetch all tier rules for interpretation."""
        if self.tier_rules_cache is None:
            print("Fetching tier rules...")
            self.tier_rules_cache = self.make_api_call("tierRules")
        return self.tier_rules_cache
    
    def fetch_clubs(self) -> Dict[str, Any]:
        """Fetch all clubs information."""
        if self.clubs_cache is None:
            print("Fetching clubs...")
            self.clubs_cache = self.make_api_call("clubs")
        return self.clubs_cache
    
    def get_club_by_id(self, club_id: int) -> Optional[Dict[str, Any]]:
        """Get club information by ID."""
        clubs_data = self.fetch_clubs()
        for club in clubs_data.get("data", []):
            if club.get("id") == club_id:
                return club
        return None
    
    def get_tier_rule_by_id(self, rule_id: int) -> Optional[Dict[str, Any]]:
        """Get tier rule information by ID."""
        tier_rules_data = self.fetch_tier_rules()
        for rule in tier_rules_data.get("data", []):
            if rule.get("id") == rule_id:
                return rule
        return None
    
    def interpret_date_range_type(self, date_range_type: str) -> str:
        """Convert date range type to human-readable text."""
        date_range_map = {
            "previous365Days": "Previous 365 Days",
            "currentYear": "Current Year",
            "previousYear": "Previous Year",
            "currentMonth": "Current Month",
            "previousMonth": "Previous Month",
            "currentWeek": "Current Week",
            "previousWeek": "Previous Week",
            "customDates": "Custom Date Range",
            "entireProgram": "Entire Program Period"
        }
        return date_range_map.get(date_range_type, date_range_type)
    
    def format_number(self, num: Any) -> str:
        """Format numbers for human readability."""
        if num is None:
            return "0"
        try:
            return f"{int(num):,}"
        except:
            return str(num)
    
    def format_date(self, date_str: str) -> str:
        """Format a date string for human readability."""
        if not date_str:
            return "Not specified"
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%B %d, %Y at %H:%M UTC")
        except:
            return date_str
    
    def interpret_tier_set_rule(self, rule_data: Dict[str, Any]) -> str:
        """Convert tier set rule data to human-readable text."""
        if not rule_data:
            return "No rule defined"
        
        parts = []
        
        # Get tier rule information
        tier_rule = rule_data.get("tierRule", {})
        if tier_rule and tier_rule.get("id"):
            tier_rule_info = self.get_tier_rule_by_id(tier_rule["id"])
            if tier_rule_info:
                parts.append(f"**Primary Qualifier:** {tier_rule_info['name']}")
        
        # Get transaction type descriptor (simplified for now)
        transaction_desc = rule_data.get("transactionTypeDescriptor", {})
        if transaction_desc and transaction_desc.get("id"):
            if transaction_desc["id"] == 1:
                parts.append("**Transaction Type Descriptor:** Do Not Filter - All Transaction Types")
            else:
                parts.append(f"**Transaction Type Descriptor:** ID {transaction_desc['id']}")
        
        # Get date range type
        date_range_type = rule_data.get("dateRangeType")
        if date_range_type:
            parts.append(f"**Date Range:** {self.interpret_date_range_type(date_range_type)}")
        
        return "\n".join(f"- {part}" for part in parts) if parts else "Rule details not available"
    
    def generate_tier_set_summary(self, tier_sets_with_details: List[Dict[str, Any]]) -> str:
        """Generate summary table for all tier sets."""
        lines = [
            "## Tier Sets Summary",
            "",
            "| ID | Name | Status | Tiers Count | Last Updated |",
            "|----|------|--------|-------------|--------------|"
        ]
        
        for tier_set in sorted(tier_sets_with_details, key=lambda x: x["id"]):
            tiers_count = len(tier_set.get("tiers", []))
            last_updated = tier_set.get("lastUpdatedTimestamp", "").split("T")[0] if tier_set.get("lastUpdatedTimestamp") else "Unknown"
            
            lines.append(
                f"| {tier_set['id']} | {tier_set['name']} | {tier_set.get('status', 'N/A')} | "
                f"{tiers_count} | {last_updated} |"
            )
        
        return "\n".join(lines)
    
    def generate_detailed_tier_sets(self, tier_sets_with_details: List[Dict[str, Any]]) -> str:
        """Generate detailed sections for each tier set."""
        lines = [
            "## Detailed Tier Sets Information",
            ""
        ]
        
        for tier_set in sorted(tier_sets_with_details, key=lambda x: x["id"]):
            lines.append(f"### {tier_set['name']} (ID: {tier_set['id']})")
            lines.append("")
            
            # Basic information
            lines.append(f"**Status:** {tier_set.get('status', 'N/A')}")
            lines.append(f"**Rebuild Settings:** {tier_set.get('rebuildSettings', 'N/A')}")
            
            if tier_set.get("lastUpdatedTimestamp"):
                lines.append(f"**Last Updated:** {self.format_date(tier_set['lastUpdatedTimestamp'])}")
            
            # Primary Qualifier Rules
            first_rule = tier_set.get("firstRule")
            second_rule = tier_set.get("secondRule")
            
            if first_rule or second_rule:
                lines.append("")
                lines.append("**Primary Qualifier Rules:**")
                
                if first_rule:
                    rule_interpretation = self.interpret_tier_set_rule(first_rule)
                    lines.append(rule_interpretation)
                
                if second_rule:
                    lines.append("")
                    lines.append("**Second Rule:**")
                    rule_interpretation = self.interpret_tier_set_rule(second_rule)
                    lines.append(rule_interpretation)
            
            # Clubs
            clubs = tier_set.get("clubs", [])
            if clubs:
                lines.append("")
                lines.append("**Associated Clubs:**")
                for club_ref in clubs:
                    club_id = club_ref.get("id") if isinstance(club_ref, dict) else club_ref
                    club = self.get_club_by_id(club_id)
                    if club:
                        lines.append(f"- {club.get('name', f'Club {club_id}')} (ID: {club_id})")
                    else:
                        lines.append(f"- Club {club_id}")
            
            # Tiers
            tiers = tier_set.get("tiers", [])
            if tiers:
                lines.append("")
                lines.append("**Tiers:**")
                lines.append("")
                lines.append("| Order | Tier Name | 1st Min Qualifying Value | 2nd Min Qualifying Value | Current Count |")
                lines.append("|-------|-----------|--------------------------|--------------------------|---------------|")
                
                for tier in sorted(tiers, key=lambda x: x.get("order", 0)):
                    # Use the correct field names from the API response
                    first_min = self.format_number(tier.get("firstQualifyingValue", 0))
                    second_min = tier.get("secondQualifyingValue")
                    second_min_str = self.format_number(second_min) if second_min is not None else "--"
                    
                    # Current count from statistics if available
                    stats = tier.get("statistics")
                    current_count = self.format_number(stats.get("memberCount", 0)) if stats else "N/A"
                    
                    lines.append(
                        f"| {tier.get('order', 'N/A')} | {tier.get('name', 'Unnamed')} | "
                        f"{first_min} | {second_min_str} | {current_count} |"
                    )
            
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_clubs_summary(self) -> str:
        """Generate a summary of all clubs."""
        clubs_data = self.fetch_clubs()
        clubs = clubs_data.get("data", [])
        
        if not clubs:
            return ""
        
        lines = [
            "## Clubs Summary",
            "",
            "| ID | Name | Description | Status |",
            "|----|------|-------------|--------|"
        ]
        
        for club in sorted(clubs, key=lambda x: x.get("id", 0)):
            description = club.get("description", "")
            if len(description) > 50:
                description = description[:47] + "..."
            
            lines.append(
                f"| {club.get('id', 'N/A')} | {club.get('name', 'Unnamed')} | "
                f"{description} | {club.get('status', 'N/A')} |"
            )
        
        lines.extend(["", ""])
        return "\n".join(lines)
    
    def generate_statistics_summary(self, tier_sets_with_details: List[Dict[str, Any]]) -> str:
        """Generate overall statistics summary."""
        total_tier_sets = len(tier_sets_with_details)
        total_tiers = sum(len(ts.get("tiers", [])) for ts in tier_sets_with_details)
        total_members = sum(
            sum(tier.get("currentCount", 0) for tier in ts.get("tiers", []))
            for ts in tier_sets_with_details
        )
        
        active_tier_sets = sum(1 for ts in tier_sets_with_details if ts.get("status") == "active")
        
        lines = [
            "## Statistics Summary",
            "",
            f"**Total Tier Sets:** {total_tier_sets}",
            f"**Active Tier Sets:** {active_tier_sets}",
            f"**Total Tiers:** {total_tiers}",
            f"**Total Members Across All Tiers:** {self.format_number(total_members)}",
            ""
        ]
        
        return "\n".join(lines)
    
    def generate_tier_report(self, output_file: str = "tiers_report.md") -> str:
        """Generate the complete tiers report."""
        print("Starting tiers report generation...")
        
        # Fetch all tier sets
        tier_sets = self.fetch_tier_sets()
        if not tier_sets:
            print("No tier sets found or API call failed.")
            return ""
        
        print(f"Found {len(tier_sets)} tier sets")
        
        # Fetch detailed information for each tier set
        tier_sets_with_details = []
        for tier_set in tier_sets:
            tier_set_details = self.fetch_tier_set_details(tier_set["id"])
            if tier_set_details:
                tier_sets_with_details.append(tier_set_details)
            time.sleep(0.1)  # Small delay to be respectful to the API
        
        # Fetch supporting data
        self.fetch_tier_rules()
        self.fetch_clubs()
        
        # Generate the report
        report_lines = [
            "# Complete Tiers Report",
            "",
            f"**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}",
            f"**Total Tier Sets:** {len(tier_sets_with_details)}",
            ""
        ]
        
        # Add statistics summary
        report_lines.append(self.generate_statistics_summary(tier_sets_with_details))
        
        # Add tier sets summary
        report_lines.append(self.generate_tier_set_summary(tier_sets_with_details))
        report_lines.append("")
        
        # Add clubs summary
        clubs_summary = self.generate_clubs_summary()
        if clubs_summary:
            report_lines.append(clubs_summary)
        
        # Add detailed sections
        report_lines.append(self.generate_detailed_tier_sets(tier_sets_with_details))
        
        # Write to file
        report_content = "\n".join(report_lines)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        print(f"Report generated successfully: {output_file}")
        return report_content





"""
Rewards Reporter
================

This script fetches rewards data from the Kognitiv Loyalty API
and generates a comprehensive markdown report with human-readable interpretations.

Usage:
    python rewards_reporter.py --token YOUR_JWT_TOKEN

Requirements:
    - requests library (pip install requests)
    - Valid JWT token for the Kognitiv Loyalty API
"""

import json
import requests
import argparse
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

class RewardsReporter:
    def __init__(self, token: str, base_url: str = "https://ca.kognitivloyalty.com/api"):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "api-version": "2025.3",
            "Content-Type": "application/json"
        }
        self.clubs_cache = None
        
    def make_api_call(self, endpoint: str) -> Dict[str, Any]:
        """Make an API call and return the JSON response."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making API call to {endpoint}: {e}")
            return {}
    
    def fetch_all_rewards(self, per_page: int = 50) -> List[Dict[str, Any]]:
        """Fetch all rewards with pagination."""
        print("Fetching rewards list...")
        all_rewards = []
        page = 1
        
        while True:
            response = self.make_api_call(f"rewards?page={page}&perPage={per_page}")
            rewards_data = response.get("data", [])
            
            if not rewards_data:
                break
                
            all_rewards.extend(rewards_data)
            print(f"Fetched page {page}: {len(rewards_data)} rewards")
            
            # Check if there are more pages
            meta = response.get("meta", {})
            pagination = meta.get("pagination", {})
            if page >= pagination.get("totalPages", 1):
                break
                
            page += 1
            time.sleep(0.1)  # Small delay between requests
        
        print(f"Total rewards fetched: {len(all_rewards)}")
        return all_rewards
    
    def fetch_reward_details(self, reward_id: int) -> Dict[str, Any]:
        """Fetch detailed information for a specific reward."""
        print(f"Fetching details for reward {reward_id}...")
        response = self.make_api_call(f"rewards/{reward_id}")
        return response.get("data", {})
    
    def fetch_clubs(self) -> Dict[str, Any]:
        """Fetch all clubs information."""
        if self.clubs_cache is None:
            print("Fetching clubs...")
            self.clubs_cache = self.make_api_call("clubs")
        return self.clubs_cache
    
    def get_club_by_id(self, club_id: int) -> Optional[Dict[str, Any]]:
        """Get club information by ID."""
        clubs_data = self.fetch_clubs()
        for club in clubs_data.get("data", []):
            if club.get("id") == club_id:
                return club
        return None
    
    def format_number(self, num: Any) -> str:
        """Format numbers for human readability."""
        if num is None:
            return "0"
        try:
            return f"{int(num):,}"
        except:
            return str(num)
    
    def format_date(self, date_str: str) -> str:
        """Format a date string for human readability."""
        if not date_str:
            return "Not specified"
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%B %d, %Y at %H:%M UTC")
        except:
            return date_str
    
    def format_currency(self, amount: Any, currency: str = "USD") -> str:
        """Format currency amounts."""
        if amount is None:
            return "N/A"
        try:
            return f"${float(amount):,.2f} {currency}"
        except:
            return str(amount)
    
    def interpret_reward_type(self, reward_type: str) -> str:
        """Convert reward type to human-readable description."""
        type_map = {
            "points": "Points Reward",
            "cash": "Cash Reward", 
            "merchandise": "Merchandise Reward",
            "experience": "Experience Reward",
            "discount": "Discount Reward",
            "freeplay": "Free Play Reward",
            "comp": "Complimentary Reward"
        }
        return type_map.get(reward_type.lower(), reward_type)
    
    def interpret_reward_status(self, status: str) -> str:
        """Convert reward status to human-readable description."""
        status_map = {
            "active": "Active",
            "inactive": "Inactive",
            "expired": "Expired",
            "pending": "Pending Approval",
            "draft": "Draft"
        }
        return status_map.get(status.lower(), status)
    
    def extract_club_info(self, reward_data: Dict[str, Any]) -> List[str]:
        """Extract and enrich club information from reward data."""
        club_info = []
        
        # Look for club references in various places
        club_fields = ["clubs", "eligibleClubs", "restrictedClubs"]
        
        for field in club_fields:
            clubs = reward_data.get(field, [])
            if clubs:
                for club_ref in clubs:
                    club_id = club_ref.get("id") if isinstance(club_ref, dict) else club_ref
                    if club_id:
                        club = self.get_club_by_id(club_id)
                        if club:
                            club_name = club.get("name", f"Club {club_id}")
                            club_info.append(f"{club_name} (ID: {club_id})")
                        else:
                            club_info.append(f"Club {club_id}")
        
        return club_info
    
    def filter_template_keys(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove template-related keys from the data."""
        template_keys = [
            "template", "templates", "templateId", "templateData",
            "emailTemplate", "smsTemplate", "pushTemplate"
        ]
        
        filtered_data = {}
        for key, value in data.items():
            if key.lower() not in [tk.lower() for tk in template_keys]:
                filtered_data[key] = value
        
        return filtered_data
    
    def generate_rewards_summary(self, rewards_with_details: List[Dict[str, Any]]) -> str:
        """Generate summary table for all rewards."""
        lines = [
            "## Rewards Summary",
            "",
            "| ID | Name | Type | Status | Points Cost | Cash Value | Available From | Available Until |",
            "|----|----- |------|--------|-------------|------------|----------------|-----------------|"
        ]
        
        for reward in sorted(rewards_with_details, key=lambda x: x.get("id", 0)):
            reward_type = self.interpret_reward_type(reward.get("type", "Unknown"))
            status = self.interpret_reward_status(reward.get("status", "Unknown"))
            points_cost = self.format_number(reward.get("pointsCost", 0))
            cash_value = self.format_currency(reward.get("cashValue"))
            
            available_from = reward.get("availableFrom", "").split("T")[0] if reward.get("availableFrom") else "N/A"
            available_until = reward.get("availableUntil", "").split("T")[0] if reward.get("availableUntil") else "N/A"
            
            lines.append(
                f"| {reward.get('id', 'N/A')} | {reward.get('name', 'Unnamed')} | {reward_type} | "
                f"{status} | {points_cost} | {cash_value} | {available_from} | {available_until} |"
            )
        
        return "\n".join(lines)
    
    def generate_detailed_rewards(self, rewards_with_details: List[Dict[str, Any]]) -> str:
        """Generate detailed sections for each reward."""
        lines = [
            "## Detailed Reward Information",
            ""
        ]
        
        for reward in sorted(rewards_with_details, key=lambda x: x.get("id", 0)):
            # Filter out template keys
            filtered_reward = self.filter_template_keys(reward)
            
            lines.append(f"### {reward.get('name', 'Unnamed Reward')} (ID: {reward.get('id', 'N/A')})")
            lines.append("")
            
            # Basic Information
            lines.append(f"**Type:** {self.interpret_reward_type(reward.get('type', 'Unknown'))}")
            lines.append(f"**Status:** {self.interpret_reward_status(reward.get('status', 'Unknown'))}")
            lines.append(f"**External Reference:** {reward.get('externalReference', 'N/A')}")
            
            if reward.get("description"):
                lines.append(f"**Description:** {reward['description']}")
            
            # Currency and Value Information
            if reward.get("minimumCurrencyAmount") is not None:
                lines.append(f"**Minimum Currency Amount:** {self.format_currency(reward['minimumCurrencyAmount'])}")
            
            if reward.get("maximumCurrencyAmount") is not None:
                lines.append(f"**Maximum Currency Amount:** {self.format_currency(reward['maximumCurrencyAmount'])}")
            
            # Points Information
            points_formula = reward.get("currencyToPointsFormula", {})
            if points_formula:
                points = points_formula.get("points", 0)
                per_value = points_formula.get("perValue", 1)
                rounding = points_formula.get("roundingType", "N/A")
                lines.append(f"**Points Formula:** {points} points per {per_value} currency unit (Rounding: {rounding})")
            
            if reward.get("deductPoints") is not None:
                lines.append(f"**Deduct Points:** {'Yes' if reward['deductPoints'] else 'No'}")
            
            # Expiry Information
            expire_type = reward.get("expireType")
            if expire_type:
                lines.append(f"**Expiry Type:** {expire_type.title()}")
                if expire_type != "never" and reward.get("expireDaysFromIssued"):
                    lines.append(f"**Expires After:** {reward['expireDaysFromIssued']} days from issue")
            
            # Limits and Restrictions
            if reward.get("issueLimit") is not None:
                lines.append(f"**Issue Limit:** {self.format_number(reward['issueLimit'])}")
            
            if reward.get("memberIssueLimit") is not None:
                lines.append(f"**Member Issue Limit:** {self.format_number(reward['memberIssueLimit'])}")
            
            if reward.get("totalLimitReached") is not None:
                lines.append(f"**Total Limit Reached:** {'Yes' if reward['totalLimitReached'] else 'No'}")
            
            # POS and Transfer Settings
            if reward.get("posEligibility"):
                lines.append(f"**POS Eligibility:** {reward['posEligibility'].replace('_', ' ').title()}")
            
            if reward.get("requireTransferTarget") is not None:
                lines.append(f"**Requires Transfer Target:** {'Yes' if reward['requireTransferTarget'] else 'No'}")
            
            # Barcode Information
            if reward.get("barCodeType"):
                lines.append(f"**Barcode Type:** {reward['barCodeType']}")
            
            # Notification Settings
            notification_settings = []
            if reward.get("sendPendingViaEmailAtEndOfDay") is not None:
                notification_settings.append(f"Email at end of day: {'Yes' if reward['sendPendingViaEmailAtEndOfDay'] else 'No'}")
            
            if reward.get("sendPendingNotificationRealTime") is not None:
                notification_settings.append(f"Real-time notifications: {'Yes' if reward['sendPendingNotificationRealTime'] else 'No'}")
            
            if notification_settings:
                lines.append(f"**Notification Settings:** {', '.join(notification_settings)}")
            
            # Club Information
            club_info = self.extract_club_info(reward)
            if club_info:
                lines.append("")
                lines.append("**Associated Clubs:**")
                for club in club_info:
                    lines.append(f"- {club}")
            
            # Promotional Member Groups
            promo_groups = reward.get("promotionalMemberGroups", [])
            if promo_groups:
                lines.append("")
                lines.append("**Promotional Member Groups:**")
                for group in promo_groups:
                    group_id = group.get("id") if isinstance(group, dict) else group
                    lines.append(f"- Group {group_id}")
            
            # Tiers
            tiers = reward.get("tiers", [])
            if tiers:
                lines.append("")
                lines.append("**Associated Tiers:**")
                for tier in tiers:
                    tier_id = tier.get("id") if isinstance(tier, dict) else tier
                    lines.append(f"- Tier {tier_id}")
            
            # Translations
            translations = reward.get("translations", [])
            if translations:
                lines.append("")
                lines.append("**Translations:**")
                for translation in translations:
                    lang_name = translation.get("language", {}).get("name", "Unknown")
                    trans_name = translation.get("name", "N/A")
                    trans_desc = translation.get("description", "N/A")
                    lines.append(f"- **{lang_name}:** {trans_name} - {trans_desc}")
            
            # Template Information (IDs only, not full template data)
            template_info = []
            template_fields = [
                ("rewardPrintTemplate", "Print Template"),
                ("deviceRewardPrintTemplate", "Device Print Template"),
                ("notifyEmailTemplate", "Notification Email Template"),
                ("certificateEmailTemplate", "Certificate Email Template"),
                ("notifyTextTemplate", "Notification Text Template"),
                ("certificateTextTemplate", "Certificate Text Template")
            ]
            
            for field, label in template_fields:
                template = reward.get(field)
                if template and isinstance(template, dict) and template.get("id"):
                    template_info.append(f"{label}: {template['id']}")
            
            if template_info:
                lines.append("")
                lines.append("**Template References:**")
                for info in template_info:
                    lines.append(f"- {info}")
            
            # Additional Settings
            if reward.get("attachPrintTemplateInPdfFormat") is not None:
                lines.append(f"**Attach Print Template as PDF:** {'Yes' if reward['attachPrintTemplateInPdfFormat'] else 'No'}")
            
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_statistics_summary(self, rewards_with_details: List[Dict[str, Any]]) -> str:
        """Generate overall statistics summary."""
        total_rewards = len(rewards_with_details)
        active_rewards = sum(1 for r in rewards_with_details if r.get("status", "").lower() == "active")
        
        # Count by type
        type_counts = {}
        for reward in rewards_with_details:
            reward_type = reward.get("type", "Unknown")
            type_counts[reward_type] = type_counts.get(reward_type, 0) + 1
        
        # Calculate total inventory
        total_inventory = sum(r.get("totalInventory", 0) or 0 for r in rewards_with_details)
        remaining_inventory = sum(r.get("remainingInventory", 0) or 0 for r in rewards_with_details if r.get("remainingInventory") is not None)
        
        lines = [
            "## Statistics Summary",
            "",
            f"**Total Rewards:** {total_rewards}",
            f"**Active Rewards:** {active_rewards}",
            f"**Total Inventory:** {self.format_number(total_inventory)}",
            f"**Remaining Inventory:** {self.format_number(remaining_inventory)}",
            "",
            "**Rewards by Type:**"
        ]
        
        for reward_type, count in sorted(type_counts.items()):
            lines.append(f"- {self.interpret_reward_type(reward_type)}: {count}")
        
        lines.append("")
        return "\n".join(lines)
    
    def generate_reward_report(self, output_file: str = "rewards_report.md") -> str:
        """Generate the complete rewards report."""
        print("Starting rewards report generation...")
        
        # Fetch all rewards
        rewards = self.fetch_all_rewards()
        if not rewards:
            print("No rewards found or API call failed.")
            return ""
        
        print(f"Found {len(rewards)} rewards")
        
        # Fetch detailed information for each reward
        rewards_with_details = []
        for reward in rewards:
            reward_details = self.fetch_reward_details(reward["id"])
            if reward_details:
                rewards_with_details.append(reward_details)
            time.sleep(0.1)  # Small delay to be respectful to the API
        
        # Fetch supporting data
        self.fetch_clubs()
        
        # Generate the report
        report_lines = [
            "# Complete Rewards Report",
            "",
            f"**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}",
            f"**Total Rewards:** {len(rewards_with_details)}",
            ""
        ]
        
        # Add statistics summary
        report_lines.append(self.generate_statistics_summary(rewards_with_details))
        
        # Add rewards summary
        report_lines.append(self.generate_rewards_summary(rewards_with_details))
        report_lines.append("")
        
        # Add detailed sections
        report_lines.append(self.generate_detailed_rewards(rewards_with_details))
        
        # Write to file
        report_content = "\n".join(report_lines)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        print(f"Report generated successfully: {output_file}")
        return report_content





"""
Complete Promotions Reporter - Final Version
============================================

This script fetches ALL promotions data from the Kognitiv Loyalty API
and generates a comprehensive markdown report designed for LLM integration.

Key Features:
- Fetches all promotions with complete pagination
- Preserves ALL data from listing calls AND detailed meta calls
- Shows promotion types (transactionProductBonus, transactionBonus, etc.)
- Enriches transaction types and clubs
- Preserves all IDs for cross-referencing with other reports
- Generates LLM-ready markdown for holistic analysis

Usage:
    python promotions_reporter_final.py --token YOUR_JWT_TOKEN

Requirements:
    - requests library (pip install requests)
    - Valid JWT token for the Kognitiv Loyalty API
"""

import json
import requests
import argparse
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

class PromotionsReporterFinal:
    def __init__(self, token: str, base_url: str = "https://ca.kognitivloyalty.com/api"):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "api-version": "2025.3",
            "Content-Type": "application/json"
        }
        self.transaction_types_cache = None
        self.clubs_cache = None
        
    def make_api_call(self, endpoint: str) -> Dict[str, Any]:
        """Make an API call and return the JSON response."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making API call to {endpoint}: {e}")
            return {}
    
    def fetch_all_promotions(self, per_page: int = 100) -> List[Dict[str, Any]]:
        """Fetch all promotions with complete pagination."""
        print("Fetching all promotions with pagination...")
        all_promotions = []
        page = 1
        
        while True:
            endpoint = f"promotions?page={page}&perPage={per_page}&status=draft&status=active&status=scheduled&status=completed&status=noStatus"
            response = self.make_api_call(endpoint)
            promotions_data = response.get("data", [])
            
            if not promotions_data:
                print(f"No more promotions found on page {page}")
                break
                
            all_promotions.extend(promotions_data)
            print(f"Fetched page {page}: {len(promotions_data)} promotions")
            
            # Continue until we get less than per_page results
            if len(promotions_data) < per_page:
                print(f"Reached end of pagination (got {len(promotions_data)} < {per_page})")
                break
                
            page += 1
            time.sleep(0.1)  # Small delay between requests
        
        print(f"Total promotions fetched: {len(all_promotions)}")
        return all_promotions
    
    def fetch_promotion_details(self, promotion_type: str, promotion_id: str) -> Dict[str, Any]:
        """Fetch detailed information for a specific promotion."""
        print(f"Fetching details for promotion {promotion_type}/{promotion_id}...")
        response = self.make_api_call(f"promotions/{promotion_type}/{promotion_id}")
        return response.get("data", {})
    
    def merge_promotion_data(self, listing_data: Dict[str, Any], detail_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge data from listing call and detail call, preserving all information."""
        merged = {}
        
        # Start with listing data
        merged.update(listing_data)
        
        # Add detail data, but don't overwrite listing data
        for key, value in detail_data.items():
            if key not in merged or merged[key] is None:
                merged[key] = value
            elif key == "statistics" and value is not None:
                # Merge statistics if both exist
                if merged.get("statistics"):
                    merged["statistics"].update(value)
                else:
                    merged["statistics"] = value
        
        # Ensure we preserve the promotion type from listing
        if "type" in listing_data:
            merged["promotionType"] = listing_data["type"]
        
        return merged
    
    def fetch_transaction_types(self) -> Dict[str, Any]:
        """Fetch all transaction types for enrichment."""
        if self.transaction_types_cache is None:
            print("Fetching transaction types...")
            self.transaction_types_cache = self.make_api_call("transactionTypes")
        return self.transaction_types_cache
    
    def fetch_clubs(self) -> Dict[str, Any]:
        """Fetch all clubs information."""
        if self.clubs_cache is None:
            print("Fetching clubs...")
            self.clubs_cache = self.make_api_call("clubs")
        return self.clubs_cache
    
    def get_transaction_type_by_id(self, transaction_type_id: int) -> Optional[Dict[str, Any]]:
        """Get transaction type information by ID."""
        transaction_types_data = self.fetch_transaction_types()
        for transaction_type in transaction_types_data.get("data", []):
            if transaction_type.get("id") == transaction_type_id:
                return transaction_type
        return None
    
    def get_club_by_id(self, club_id: int) -> Optional[Dict[str, Any]]:
        """Get club information by ID."""
        clubs_data = self.fetch_clubs()
        for club in clubs_data.get("data", []):
            if club.get("id") == club_id:
                return club
        return None
    
    def format_number(self, num: Any) -> str:
        """Format numbers for human readability."""
        if num is None:
            return "0"
        try:
            return f"{int(num):,}"
        except:
            return str(num)
    
    def format_date(self, date_str: str) -> str:
        """Format a date string for human readability."""
        if not date_str:
            return "Not specified"
        try:
            dt = datetime.fromisoformat(date_str)
            return dt.strftime("%B %d, %Y")
        except:
            return date_str
    
    def format_date_range(self, date_range: Dict[str, str]) -> str:
        """Format a date range for human readability."""
        if not date_range:
            return "Not specified"
        
        start = date_range.get("start", "")
        end = date_range.get("end", "")
        
        if start and end:
            return f"{self.format_date(start)} - {self.format_date(end)}"
        elif start:
            return f"From {self.format_date(start)}"
        elif end:
            return f"Until {self.format_date(end)}"
        else:
            return "Not specified"
    
    def interpret_promotion_status(self, status: str) -> str:
        """Convert promotion status to human-readable description."""
        status_map = {
            "active": "Active",
            "draft": "Draft",
            "scheduled": "Scheduled",
            "completed": "Completed",
            "noStatus": "No Status",
            "inactive": "Inactive",
            "expired": "Expired"
        }
        return status_map.get(status.lower(), status) if status else "Unknown"
    
    def interpret_bonus_type(self, bonus_type: str) -> str:
        """Convert bonus type to human-readable description."""
        bonus_type_map = {
            "percentagePoints": "Percentage Points",
            "fixedPoints": "Fixed Points",
            "percentageDiscount": "Percentage Discount",
            "fixedDiscount": "Fixed Discount",
            "freeProduct": "Free Product",
            "multiplierPoints": "Multiplier Points"
        }
        return bonus_type_map.get(bonus_type, bonus_type) if bonus_type else ""
    
    def format_valid_days(self, valid_days: List[str]) -> str:
        """Format valid days list for human readability."""
        if not valid_days:
            return "Not specified"
        
        day_map = {
            "sunday": "Sunday",
            "monday": "Monday", 
            "tuesday": "Tuesday",
            "wednesday": "Wednesday",
            "thursday": "Thursday",
            "friday": "Friday",
            "saturday": "Saturday"
        }
        
        formatted_days = [day_map.get(day.lower(), day) for day in valid_days]
        
        if len(formatted_days) == 7:
            return "All days"
        else:
            return ", ".join(formatted_days)
    
    def generate_promotions_summary(self, promotions_with_details: List[Dict[str, Any]]) -> str:
        """Generate summary table for all promotions."""
        lines = [
            "## Promotions Summary",
            "",
            "| ID | Name | Type | Status | Activity Period | Bonus Type | Bonus Value | Frequency |",
            "|----|------|------|--------|-----------------|------------|-------------|-----------|"
        ]
        
        for promo in sorted(promotions_with_details, key=lambda x: (x.get("promotionType", ""), int(x.get("id", 0)))):
            promo_type = promo.get("promotionType", "Unknown")
            status = self.interpret_promotion_status(promo.get("status", "Unknown"))
            frequency = promo.get("frequency", "").title() if promo.get("frequency") else "N/A"
            
            # Get activity date range
            activity_range = promo.get("activityDateRange") or promo.get("dateRange")
            if activity_range:
                period = self.format_date_range(activity_range)
            else:
                period = "Not specified"
            
            # Get bonus information
            bonus_type = self.interpret_bonus_type(promo.get("bonusType", ""))
            bonus_value = ""
            
            if promo.get("percentageOfPoints"):
                bonus_value = f"{promo['percentageOfPoints']}%"
            elif promo.get("fixedPoints"):
                bonus_value = f"{self.format_number(promo['fixedPoints'])} pts"
            elif promo.get("multiplier"):
                bonus_value = f"{promo['multiplier']}x"
            
            lines.append(
                f"| {promo.get('id', 'N/A')} | {promo.get('name', 'Unnamed')} | {promo_type} | "
                f"{status} | {period} | {bonus_type} | {bonus_value} | {frequency} |"
            )
        
        return "\n".join(lines)
    
    def generate_detailed_promotions(self, promotions_with_details: List[Dict[str, Any]]) -> str:
        """Generate detailed sections for each promotion."""
        lines = [
            "## Detailed Promotion Information",
            "",
            "*Note: IDs are preserved for cross-referencing with other loyalty system components (tiers, groups, products, locations, etc.)*",
            ""
        ]
        
        for promo in sorted(promotions_with_details, key=lambda x: (x.get("promotionType", ""), int(x.get("id", 0)))):
            lines.append(f"### {promo.get('name', 'Unnamed Promotion')} (ID: {promo.get('id', 'N/A')})")
            lines.append("")
            
            # Basic Information from both listing and details
            lines.append(f"**Promotion Type:** {promo.get('promotionType', 'Unknown')}")
            lines.append(f"**Status:** {self.interpret_promotion_status(promo.get('status', 'Unknown'))}")
            
            if promo.get("externalReference"):
                lines.append(f"**External Reference:** {promo['externalReference']}")
            
            if promo.get("description"):
                lines.append(f"**Description:** {promo['description'].strip()}")
            
            # Frequency from listing call
            if promo.get("frequency"):
                lines.append(f"**Frequency:** {promo['frequency'].title()}")
            
            # Date Ranges
            activity_range = promo.get("activityDateRange") or promo.get("dateRange")
            if activity_range:
                lines.append(f"**Activity Period:** {self.format_date_range(activity_range)}")
            
            booking_range = promo.get("bookingDateRange")
            if booking_range:
                lines.append(f"**Booking Period:** {self.format_date_range(booking_range)}")
            
            # Bonus Information
            if promo.get("bonusType"):
                lines.append(f"**Bonus Type:** {self.interpret_bonus_type(promo['bonusType'])}")
            
            if promo.get("percentageOfPoints"):
                lines.append(f"**Percentage of Points:** {promo['percentageOfPoints']}%")
            
            if promo.get("fixedPoints"):
                lines.append(f"**Fixed Points:** {self.format_number(promo['fixedPoints'])}")
            
            if promo.get("multiplier"):
                lines.append(f"**Points Multiplier:** {promo['multiplier']}x")
            
            if promo.get("pointsRounding"):
                lines.append(f"**Points Rounding:** {promo['pointsRounding']}")
            
            # Validity and Limits
            valid_days = promo.get("validOnDays", [])
            if valid_days:
                lines.append(f"**Valid Days:** {self.format_valid_days(valid_days)}")
            
            if promo.get("limit"):
                lines.append(f"**Limit:** {promo['limit'].title()}")
            
            # Activation Promotion from listing call
            if promo.get("activationPromotion"):
                lines.append("")
                lines.append("**Activation Promotion:**")
                activation = promo["activationPromotion"]
                if isinstance(activation, dict):
                    lines.append(f"- Promotion ID: {activation.get('id')}")
                    if activation.get("name"):
                        lines.append(f"- Name: {activation['name']}")
                else:
                    lines.append(f"- {activation}")
            
            # Transaction Types (Enriched)
            transaction_types = promo.get("transactionTypes", [])
            if transaction_types:
                lines.append("")
                lines.append("**Transaction Types:**")
                for tt in transaction_types:
                    tt_id = tt.get("id") if isinstance(tt, dict) else tt
                    tt_details = self.get_transaction_type_by_id(tt_id)
                    if tt_details:
                        lines.append(f"- {tt_details.get('name', f'Transaction Type {tt_id}')} (ID: {tt_id})")
                    else:
                        lines.append(f"- Transaction Type ID: {tt_id}")
            
            # Product Groups (IDs preserved for cross-reference)
            product_groups = promo.get("productGroups", [])
            if product_groups:
                lines.append("")
                lines.append("**Product Groups:** *(IDs for cross-reference with product groups report)*")
                for pg in product_groups:
                    pg_id = pg.get("id") if isinstance(pg, dict) else pg
                    lines.append(f"- Product Group ID: {pg_id}")
            
            # Location Information
            if promo.get("allLocations"):
                lines.append("")
                lines.append("**Locations:** All locations")
            else:
                location_groups = promo.get("locationGroups", [])
                if location_groups:
                    lines.append("")
                    lines.append("**Location Groups:** *(IDs for cross-reference with location groups report)*")
                    for lg in location_groups:
                        lg_id = lg.get("id") if isinstance(lg, dict) else lg
                        lines.append(f"- Location Group ID: {lg_id}")
            
            # Clubs (Enriched)
            clubs = promo.get("clubs", [])
            if clubs:
                lines.append("")
                lines.append("**Associated Clubs:**")
                for club_ref in clubs:
                    club_id = club_ref.get("id") if isinstance(club_ref, dict) else club_ref
                    club_details = self.get_club_by_id(club_id)
                    if club_details:
                        lines.append(f"- {club_details.get('name', f'Club {club_id}')} (ID: {club_id})")
                    else:
                        lines.append(f"- Club ID: {club_id}")
            
            # Member Groups (IDs preserved for cross-reference)
            member_groups = promo.get("memberGroups", [])
            if member_groups:
                lines.append("")
                lines.append("**Member Groups:** *(IDs for cross-reference with audience groups report)*")
                for mg in member_groups:
                    mg_id = mg.get("id") if isinstance(mg, dict) else mg
                    lines.append(f"- Member Group ID: {mg_id}")
            
            # Tiers (IDs preserved for cross-reference)
            tiers = promo.get("tiers", [])
            if tiers:
                lines.append("")
                lines.append("**Tiers:** *(IDs for cross-reference with tiers report)*")
                for tier in tiers:
                    tier_id = tier.get("id") if isinstance(tier, dict) else tier
                    lines.append(f"- Tier ID: {tier_id}")
            
            # Statistics
            if promo.get("statistics"):
                lines.append("")
                lines.append("**Statistics:**")
                stats = promo["statistics"]
                for key, value in stats.items():
                    if value is not None:
                        lines.append(f"- {key.replace('_', ' ').title()}: {self.format_number(value)}")
            
            # Additional fields that might be present
            additional_fields = [
                "minimumSpendAmount", "maximumSpendAmount", "minimumQuantity", "maximumQuantity",
                "isStackable", "priority", "maxUsagePerMember", "maxUsagePerDay", "maxUsageTotal"
            ]
            
            additional_info = []
            for field in additional_fields:
                if promo.get(field) is not None:
                    value = promo[field]
                    if isinstance(value, bool):
                        additional_info.append(f"- {field.replace('_', ' ').title()}: {'Yes' if value else 'No'}")
                    else:
                        additional_info.append(f"- {field.replace('_', ' ').title()}: {self.format_number(value)}")
            
            if additional_info:
                lines.append("")
                lines.append("**Additional Information:**")
                lines.extend(additional_info)
            
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_statistics_summary(self, promotions_with_details: List[Dict[str, Any]]) -> str:
        """Generate overall statistics summary."""
        total_promotions = len(promotions_with_details)
        
        # Count by status
        status_counts = {}
        for promo in promotions_with_details:
            status = promo.get("status", "Unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by promotion type
        type_counts = {}
        for promo in promotions_with_details:
            promo_type = promo.get("promotionType", "Unknown")
            type_counts[promo_type] = type_counts.get(promo_type, 0) + 1
        
        # Count by frequency
        frequency_counts = {}
        for promo in promotions_with_details:
            frequency = promo.get("frequency", "Unknown")
            frequency_counts[frequency] = frequency_counts.get(frequency, 0) + 1
        
        # Count by year
        year_counts = {}
        for promo in promotions_with_details:
            activity_range = promo.get("activityDateRange") or promo.get("dateRange")
            if activity_range:
                start_date = activity_range.get("start", "")
                if start_date:
                    try:
                        year = datetime.fromisoformat(start_date).year
                        year_counts[year] = year_counts.get(year, 0) + 1
                    except:
                        pass
        
        lines = [
            "## Statistics Summary",
            "",
            f"**Total Promotions:** {total_promotions}",
            "",
            "**Promotions by Status:**"
        ]
        
        for status, count in sorted(status_counts.items()):
            lines.append(f"- {self.interpret_promotion_status(status)}: {count}")
        
        lines.append("")
        lines.append("**Promotions by Type:**")
        for promo_type, count in sorted(type_counts.items()):
            lines.append(f"- {promo_type}: {count}")
        
        lines.append("")
        lines.append("**Promotions by Frequency:**")
        for frequency, count in sorted(frequency_counts.items()):
            lines.append(f"- {frequency.title() if frequency else 'Unknown'}: {count}")
        
        if year_counts:
            lines.append("")
            lines.append("**Promotions by Start Year:**")
            for year, count in sorted(year_counts.items()):
                lines.append(f"- {year}: {count}")
        
        lines.append("")
        return "\n".join(lines)
    
    def generate_cross_reference_guide(self) -> str:
        """Generate a guide for cross-referencing with other reports."""
        lines = [
            "## Cross-Reference Guide for LLM Integration",
            "",
            "This promotions report contains IDs that can be cross-referenced with other loyalty system reports:",
            "",
            "**Product Group IDs** → Match with Product Groups Report",
            "- Use Product Group IDs to understand which products are included in promotions",
            "- Analyze promotion effectiveness by product category",
            "",
            "**Location Group IDs** → Match with Location Groups Report", 
            "- Use Location Group IDs to understand geographical promotion targeting",
            "- Analyze regional promotion performance",
            "",
            "**Member Group IDs** → Match with Audience Groups Report",
            "- Use Member Group IDs to understand customer segmentation in promotions",
            "- Analyze promotion targeting strategies",
            "",
            "**Tier IDs** → Match with Tiers Report",
            "- Use Tier IDs to understand tier-specific promotions",
            "- Analyze promotion benefits by customer tier",
            "",
            "**Club IDs** → Already enriched with club names and details",
            "- Use club information to understand membership-based promotions",
            "",
            "**Transaction Type IDs** → Already enriched with transaction type names",
            "- Use transaction type information to understand promotion triggers",
            "",
            "**Promotion Types** → Key for understanding promotion mechanics:",
            "- `transactionProductBonus`: Product-based bonus promotions",
            "- `transactionBonus`: General transaction-based bonuses", 
            "- `fixedPoint`: Fixed point rewards",
            "- `dealOfTheDay`: Daily deal promotions",
            "- `enrollmentPoint`: Enrollment-based point rewards",
            "",
            "**Integration Strategy:**",
            "- Combine this report with others to create a complete promotional ecosystem view",
            "- Use IDs as linking keys between different system components",
            "- Analyze promotion effectiveness across products, locations, customer segments, and tiers",
            "- Use promotion types to understand different promotional mechanics",
            ""
        ]
        
        return "\n".join(lines)
    
    def generate_promotion_report(self, output_file: str = "promotions_complete_report.md") -> str:
        """Generate the complete promotions report."""
        print("Starting complete promotions report generation...")
        
        # Fetch all promotions with complete pagination
        promotions_listing = self.fetch_all_promotions()
        if not promotions_listing:
            print("No promotions found or API call failed.")
            return ""
        
        print(f"Found {len(promotions_listing)} promotions")
        
        # Fetch detailed information for each promotion and merge with listing data
        promotions_with_details = []
        successful_fetches = 0
        failed_fetches = 0
        
        for listing_promo in promotions_listing:
            promo_type = listing_promo.get("type")
            promo_id = listing_promo.get("id")
            
            if promo_type and promo_id:
                detail_data = self.fetch_promotion_details(promo_type, promo_id)
                if detail_data:
                    # Merge listing and detail data
                    merged_promo = self.merge_promotion_data(listing_promo, detail_data)
                    promotions_with_details.append(merged_promo)
                    successful_fetches += 1
                else:
                    # If detail fetch fails, still include listing data
                    listing_promo["promotionType"] = promo_type
                    promotions_with_details.append(listing_promo)
                    failed_fetches += 1
                    
                time.sleep(0.1)  # Small delay to be respectful to the API
        
        print(f"Successfully enriched {successful_fetches} promotions")
        if failed_fetches > 0:
            print(f"Failed to fetch details for {failed_fetches} promotions (included listing data only)")
        
        # Fetch supporting data
        self.fetch_transaction_types()
        self.fetch_clubs()
        
        # Generate the report
        report_lines = [
            "# Complete Promotions Report",
            "",
            f"**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}",
            f"**Total Promotions:** {len(promotions_with_details)}",
            f"**Successfully Enriched:** {successful_fetches}",
            f"**Listing Data Only:** {failed_fetches}",
            "",
            "*This report is designed for LLM integration with other loyalty system components.*",
            "*All IDs are preserved for cross-referencing and holistic analysis.*",
            "*All data from both listing calls and detailed meta calls is preserved.*",
            ""
        ]
        
        # Add cross-reference guide
        report_lines.append(self.generate_cross_reference_guide())
        
        # Add statistics summary
        report_lines.append(self.generate_statistics_summary(promotions_with_details))
        
        # Add promotions summary
        report_lines.append(self.generate_promotions_summary(promotions_with_details))
        report_lines.append("")
        
        # Add detailed sections
        report_lines.append(self.generate_detailed_promotions(promotions_with_details))
        
        # Write to file
        report_content = "\n".join(report_lines)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        print(f"Complete report generated successfully: {output_file}")
        return report_content








"""
Audience Groups Reporter
========================

This script fetches audience group data from the Kognitiv Loyalty API
and generates a comprehensive markdown report with human-readable interpretations.

Usage:
    python audience_groups_reporter.py --token YOUR_JWT_TOKEN

Requirements:
    - requests library (pip install requests)
    - Valid JWT token for the Kognitiv Loyalty API
"""

import json
import requests
import argparse
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

class AudienceGroupsReporter:
    def __init__(self, token: str, base_url: str = "https://ca.kognitivloyalty.com/api"):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "api-version": "2025.3",
            "Content-Type": "application/json"
        }
        self.rule_definitions = None
        
    def make_api_call(self, endpoint: str) -> Dict[str, Any]:
        """Make an API call and return the JSON response."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making API call to {endpoint}: {e}")
            return {}
    
    def fetch_audience_groups(self) -> List[Dict[str, Any]]:
        """Fetch the list of all audience groups."""
        print("Fetching audience groups list...")
        response = self.make_api_call("groups/promotionalMember")
        return response.get("data", [])
    
    def fetch_audience_group_details(self, group_id: int) -> Dict[str, Any]:
        """Fetch detailed information for a specific audience group."""
        print(f"Fetching details for audience group {group_id}...")
        response = self.make_api_call(f"groups/promotionalMember/{group_id}/rules")
        return response.get("data", {})
    
    def fetch_rule_definitions(self) -> Dict[str, Any]:
        """Fetch all rule definitions for interpretation."""
        if self.rule_definitions is None:
            print("Fetching rule definitions...")
            self.rule_definitions = self.make_api_call("groups/ruleDefinitions")
        return self.rule_definitions
    
    def get_rule_definition(self, rule_def_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific rule definition by ID."""
        rule_defs = self.fetch_rule_definitions()
        for rule_def in rule_defs.get("data", []):
            if rule_def["id"] == rule_def_id:
                return rule_def
        return None
    
    def get_component_definition(self, rule_def: Dict[str, Any], comp_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific component definition from a rule definition."""
        if rule_def:
            for component in rule_def.get("components", []):
                if component["id"] == comp_id:
                    return component
        return None
    
    def format_date(self, date_str: str) -> str:
        """Format a date string for human readability."""
        if not date_str:
            return "Not specified"
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%B %d, %Y")
        except:
            return date_str
    
    def format_number(self, num: Any) -> str:
        """Format numbers for human readability."""
        if num is None:
            return "0"
        try:
            return f"{int(num):,}"
        except:
            return str(num)
    
    def interpret_operator(self, operator: str) -> str:
        """Convert API operators to human-readable text."""
        operator_map = {
            "isEqual": "equals",
            "isNotEqual": "does not equal",
            "isGreaterThan": "is greater than",
            "isLessThan": "is less than",
            "isGreaterThanOrEqualTo": "is greater than or equal to",
            "isLessThanOrEqualTo": "is less than or equal to",
            "isBetween": "is between",
            "customDates": "custom date range",
            "entireProgram": "entire program period",
            "currentDay": "current day",
            "previousDay": "previous day",
            "currentWeek": "current week",
            "previousWeek": "previous week",
            "currentMonth": "current month",
            "previousMonth": "previous month",
            "currentYear": "current year",
            "previousYear": "previous year"
        }
        return operator_map.get(operator, operator)
    
    def interpret_rule(self, rule: Dict[str, Any]) -> str:
        """Convert a rule object to human-readable text."""
        try:
            rule_definition = rule.get("ruleDefinition")
            if not rule_definition:
                return "Rule definition not found"
            
            rule_def_id = rule_definition.get("id")
            if not rule_def_id:
                return "Rule definition ID not found"
                
            rule_def = self.get_rule_definition(rule_def_id)
            
            if not rule_def:
                return f"Unknown rule type (ID: {rule_def_id})"
            
            rule_name = rule_def["name"]
            conditions = []
            
            for value in rule.get("values", []):
                comp_def = self.get_component_definition(rule_def, value["component"]["id"])
                if comp_def:
                    label = comp_def["label"]
                    operator = self.interpret_operator(value["operator"])
                    
                    if value.get("selectedText"):
                        condition_value = value["selectedText"]
                    elif value.get("value1") and value.get("value2"):
                        condition_value = f"{self.format_date(value['value1'])} to {self.format_date(value['value2'])}"
                    elif value.get("value1"):
                        condition_value = value["value1"]
                    else:
                        condition_value = "Not specified"
                    
                    conditions.append(f"{label} {operator} {condition_value}")
            
            if conditions:
                return f"{rule_name}: {' AND '.join(conditions)}"
            else:
                return rule_name
        except Exception as e:
            return f"Error interpreting rule: {str(e)}"
    
    def generate_summary_table(self, groups_with_details: List[Dict[str, Any]]) -> str:
        """Generate the summary table for all audience groups."""
        lines = [
            "## Summary",
            "",
            "| ID | Name | Status | Rebuild | Logic | Rules | Last Built |",
            "|----|------|--------|---------|-------|-------|------------|"
        ]
        
        for group_info in sorted(groups_with_details, key=lambda x: x["group"]["id"]):
            group = group_info["group"]
            rules = group_info["rules"]
            
            # Handle both dict and list formats for rules
            if isinstance(rules, dict):
                rule_count = len(rules.get("rules", []))
                rule_match = rules.get('ruleMatch', 'N/A')
            else:
                rule_count = len(rules) if rules else 0
                rule_match = 'N/A'
            
            last_built = group.get("lastBuiltTimestamp", "").split("T")[0] if group.get("lastBuiltTimestamp") else "Unknown"
            
            lines.append(
                f"| {group['id']} | {group['name']} | {group['status']} | "
                f"{group['rebuildFrequency']} | {rule_match} | {rule_count} | {last_built} |"
            )
        
        return "\n".join(lines)
    
    def generate_detailed_sections(self, groups_with_details: List[Dict[str, Any]]) -> str:
        """Generate detailed sections for each audience group."""
        lines = [
            "## Detailed Rules for Each Audience Group",
            ""
        ]
        
        for group_info in sorted(groups_with_details, key=lambda x: x["group"]["id"]):
            group = group_info["group"]
            rules_data = group_info["rules"]
            
            lines.append(f"### {group['name']} (ID: {group['id']})")
            lines.append("")
            lines.append(f"**Status:** {group['status']}")
            
            # Handle both dict and list formats for rules_data
            if isinstance(rules_data, dict):
                rule_match = rules_data.get('ruleMatch', 'any')
                rules = rules_data.get("rules", [])
            else:
                rule_match = 'any'
                rules = rules_data if rules_data else []
            
            rule_match_text = "ANY" if rule_match == 'any' else "ALL"
            lines.append(f"**Rule Logic:** {rule_match} (member qualifies if they match {rule_match_text} of the rules)")
            lines.append(f"**Rebuild Frequency:** {group['rebuildFrequency']}")
            
            if group.get("lastBuiltTimestamp"):
                try:
                    last_built = datetime.fromisoformat(group["lastBuiltTimestamp"].replace('Z', '+00:00'))
                    lines.append(f"**Last Built:** {last_built.strftime('%B %d, %Y at %H:%M UTC')}")
                except:
                    lines.append(f"**Last Built:** {group['lastBuiltTimestamp']}")
            
            if rules:
                lines.append("")
                lines.append("**Rules:**")
                for i, rule in enumerate(rules, 1):
                    interpretation = self.interpret_rule(rule)
                    lines.append(f"{i}. {interpretation}")
            else:
                lines.append("")
                lines.append("**Rules:** No specific rules defined (likely uses default criteria)")
            
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_statistics_summary(self, groups_with_details: List[Dict[str, Any]]) -> str:
        """Generate a statistics summary section."""
        lines = [
            "## Statistics Summary",
            ""
        ]
        
        active_groups = 0
        daily_groups = 0
        monthly_groups = 0
        manual_groups = 0
        realtime_groups = 0
        
        for group_info in groups_with_details:
            group = group_info["group"]
            
            if group.get("status") == "valid":
                active_groups += 1
            
            rebuild_freq = group.get("rebuildFrequency", "")
            if rebuild_freq == "daily":
                daily_groups += 1
            elif rebuild_freq == "monthly":
                monthly_groups += 1
            elif rebuild_freq == "manual":
                manual_groups += 1
            elif rebuild_freq == "realTime":
                realtime_groups += 1
        
        lines.extend([
            f"**Total Audience Groups:** {len(groups_with_details)}",
            f"**Active Groups:** {active_groups}",
            "",
            "**Rebuild Frequency Distribution:**",
            f"- Daily: {daily_groups} groups",
            f"- Monthly: {monthly_groups} groups", 
            f"- Manual: {manual_groups} groups",
            f"- Real-time: {realtime_groups} groups",
            ""
        ])
        
        return "\n".join(lines)
    
    def generate_audience_report(self, output_file: str = "audience_groups_report.md") -> str:
        """Generate the complete audience groups report."""
        print("Starting audience groups report generation...")
        
        # Fetch all audience groups
        audience_groups = self.fetch_audience_groups()
        if not audience_groups:
            print("No audience groups found or API call failed.")
            return ""
        
        print(f"Found {len(audience_groups)} audience groups")
        
        # Fetch detailed information for each group
        groups_with_details = []
        for group in audience_groups:
            group_rules = self.fetch_audience_group_details(group["id"])
            if group_rules:
                groups_with_details.append({
                    "group": group,
                    "rules": group_rules
                })
            time.sleep(0.1)  # Small delay to be respectful to the API
        
        # Fetch rule definitions for interpretation
        self.fetch_rule_definitions()
        
        # Generate the report
        report_lines = [
            "# Complete Audience Groups Report",
            "",
            f"**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}",
            f"**Total Audience Groups:** {len(groups_with_details)}",
            ""
        ]
        
        # Add statistics summary
        report_lines.append(self.generate_statistics_summary(groups_with_details))
        
        # Add summary table
        report_lines.append(self.generate_summary_table(groups_with_details))
        report_lines.append("")
        
        # Add detailed sections
        report_lines.append(self.generate_detailed_sections(groups_with_details))
        
        # Write to file
        report_content = "\n".join(report_lines)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        print(f"Report generated successfully: {output_file}")
        return report_content







"""
Product Groups Reporter
=======================

This script fetches product group data from the Kognitiv Loyalty API
and generates a comprehensive markdown report with human-readable interpretations.

Usage:
    python product_groups_reporter.py --token YOUR_JWT_TOKEN

Requirements:
    - requests library (pip install requests)
    - Valid JWT token for the Kognitiv Loyalty API
"""

import json
import requests
import argparse
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

class ProductGroupsReporter:
    def __init__(self, token: str, base_url: str = "https://ca.kognitivloyalty.com/api"):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "api-version": "2025.3",
            "Content-Type": "application/json"
        }
        self.rule_definitions = None
        
    def make_api_call(self, endpoint: str) -> Dict[str, Any]:
        """Make an API call and return the JSON response."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making API call to {endpoint}: {e}")
            return {}
    
    def fetch_product_groups(self) -> List[Dict[str, Any]]:
        """Fetch the list of all product groups with statistics."""
        print("Fetching product groups list...")
        response = self.make_api_call("groups/product?statistics=true")
        return response.get("data", [])
    
    def fetch_product_group_details(self, group_id: int) -> Dict[str, Any]:
        """Fetch detailed information for a specific product group."""
        print(f"Fetching details for product group {group_id}...")
        response = self.make_api_call(f"groups/product/{group_id}")
        return response.get("data", {})
    
    def fetch_rule_definitions(self) -> Dict[str, Any]:
        """Fetch all rule definitions for interpretation."""
        if self.rule_definitions is None:
            print("Fetching rule definitions...")
            self.rule_definitions = self.make_api_call("groups/ruleDefinitions")
        return self.rule_definitions
    
    def get_rule_definition(self, rule_def_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific rule definition by ID."""
        rule_defs = self.fetch_rule_definitions()
        for rule_def in rule_defs.get("data", []):
            if rule_def["id"] == rule_def_id:
                return rule_def
        return None
    
    def get_component_definition(self, rule_def: Dict[str, Any], comp_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific component definition from a rule definition."""
        if rule_def:
            for component in rule_def.get("components", []):
                if component["id"] == comp_id:
                    return component
        return None
    
    def format_date(self, date_str: str) -> str:
        """Format a date string for human readability."""
        if not date_str:
            return "Not specified"
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%B %d, %Y")
        except:
            return date_str
    
    def format_number(self, num: Any) -> str:
        """Format numbers for human readability."""
        if num is None:
            return "0"
        try:
            return f"{int(num):,}"
        except:
            return str(num)
    
    def interpret_operator(self, operator: str) -> str:
        """Convert API operators to human-readable text."""
        operator_map = {
            "isEqual": "equals",
            "isNotEqual": "does not equal",
            "isGreaterThan": "is greater than",
            "isLessThan": "is less than",
            "isGreaterThanOrEqualTo": "is greater than or equal to",
            "isLessThanOrEqualTo": "is less than or equal to",
            "isBetween": "is between",
            "customDates": "custom date range",
            "entireProgram": "entire program period",
            "currentDay": "current day",
            "previousDay": "previous day",
            "currentWeek": "current week",
            "previousWeek": "previous week",
            "currentMonth": "current month",
            "previousMonth": "previous month",
            "currentYear": "current year",
            "previousYear": "previous year"
        }
        return operator_map.get(operator, operator)
    
    def interpret_rule(self, rule: Dict[str, Any]) -> str:
        """Convert a rule object to human-readable text."""
        rule_def_id = rule["ruleDefinition"]["id"]
        rule_def = self.get_rule_definition(rule_def_id)
        
        if not rule_def:
            return f"Unknown rule type (ID: {rule_def_id})"
        
        rule_name = rule_def["name"]
        conditions = []
        
        for value in rule.get("values", []):
            comp_def = self.get_component_definition(rule_def, value["component"]["id"])
            if comp_def:
                label = comp_def["label"]
                operator = self.interpret_operator(value["operator"])
                
                if value.get("selectedText"):
                    condition_value = value["selectedText"]
                elif value.get("value1") and value.get("value2"):
                    condition_value = f"{self.format_date(value['value1'])} to {self.format_date(value['value2'])}"
                elif value.get("value1"):
                    condition_value = value["value1"]
                else:
                    condition_value = "Not specified"
                
                conditions.append(f"{label} {operator} {condition_value}")
        
        if conditions:
            return f"{rule_name}: {' AND '.join(conditions)}"
        else:
            return rule_name
    
    def generate_summary_table(self, groups_with_details: List[Dict[str, Any]]) -> str:
        """Generate the summary table for all product groups."""
        lines = [
            "## Summary",
            "",
            "| ID | Name | Status | Rebuild | Logic | Rules | Members | Last Built |",
            "|----|------|--------|---------|-------|-------|---------|------------|"
        ]
        
        for group in sorted(groups_with_details, key=lambda x: x["id"]):
            rule_count = len(group.get("rules", []))
            member_count = self.format_number(group.get("statistics", {}).get("memberCount", 0))
            last_built = group.get("lastBuiltTimestamp", "").split("T")[0] if group.get("lastBuiltTimestamp") else "Unknown"
            
            lines.append(
                f"| {group['id']} | {group['name']} | {group['status']} | "
                f"{group['rebuildFrequency']} | {group['ruleMatch']} | {rule_count} | {member_count} | {last_built} |"
            )
        
        return "\n".join(lines)
    
    def generate_detailed_sections(self, groups_with_details: List[Dict[str, Any]]) -> str:
        """Generate detailed sections for each product group."""
        lines = [
            "## Detailed Rules for Each Product Group",
            ""
        ]
        
        for group in sorted(groups_with_details, key=lambda x: x["id"]):
            lines.append(f"### {group['name']} (ID: {group['id']})")
            lines.append("")
            lines.append(f"**Status:** {group['status']}")
            
            rule_match_text = "ANY" if group['ruleMatch'] == 'any' else "ALL"
            lines.append(f"**Rule Logic:** {group['ruleMatch']} (member qualifies if they match {rule_match_text} of the rules)")
            lines.append(f"**Rebuild Frequency:** {group['rebuildFrequency']}")
            
            # Add statistics if available
            stats = group.get("statistics", {})
            if stats:
                member_count = self.format_number(stats.get("memberCount", 0))
                lines.append(f"**Member Count:** {member_count}")
                
                if stats.get("lastBuiltTimestamp"):
                    try:
                        last_built = datetime.fromisoformat(stats["lastBuiltTimestamp"].replace('Z', '+00:00'))
                        lines.append(f"**Statistics Last Updated:** {last_built.strftime('%B %d, %Y at %H:%M UTC')}")
                    except:
                        lines.append(f"**Statistics Last Updated:** {stats['lastBuiltTimestamp']}")
            
            if group.get("lastBuiltTimestamp"):
                try:
                    last_built = datetime.fromisoformat(group["lastBuiltTimestamp"].replace('Z', '+00:00'))
                    lines.append(f"**Last Built:** {last_built.strftime('%B %d, %Y at %H:%M UTC')}")
                except:
                    lines.append(f"**Last Built:** {group['lastBuiltTimestamp']}")
            
            rules = group.get("rules", [])
            if rules:
                lines.append("")
                lines.append("**Rules:**")
                for i, rule in enumerate(rules, 1):
                    interpretation = self.interpret_rule(rule)
                    lines.append(f"{i}. {interpretation}")
            else:
                lines.append("")
                lines.append("**Rules:** No specific rules defined (likely uses default criteria)")
            
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_statistics_summary(self, groups_with_details: List[Dict[str, Any]]) -> str:
        """Generate a statistics summary section."""
        lines = [
            "## Statistics Summary",
            ""
        ]
        
        total_members = 0
        active_groups = 0
        daily_groups = 0
        monthly_groups = 0
        manual_groups = 0
        realtime_groups = 0
        
        for group in groups_with_details:
            stats = group.get("statistics", {})
            member_count = stats.get("memberCount", 0) or 0
            total_members += member_count
            
            if group.get("status") == "valid":
                active_groups += 1
            
            rebuild_freq = group.get("rebuildFrequency", "")
            if rebuild_freq == "daily":
                daily_groups += 1
            elif rebuild_freq == "monthly":
                monthly_groups += 1
            elif rebuild_freq == "manual":
                manual_groups += 1
            elif rebuild_freq == "realTime":
                realtime_groups += 1
        
        lines.extend([
            f"**Total Product Groups:** {len(groups_with_details)}",
            f"**Active Groups:** {active_groups}",
            f"**Total Members Across All Groups:** {self.format_number(total_members)}",
            "",
            "**Rebuild Frequency Distribution:**",
            f"- Daily: {daily_groups} groups",
            f"- Monthly: {monthly_groups} groups", 
            f"- Manual: {manual_groups} groups",
            f"- Real-time: {realtime_groups} groups",
            ""
        ])
        
        return "\n".join(lines)
    
    def generate_product_report(self, output_file: str = "product_groups_report.md") -> str:
        """Generate the complete product groups report."""
        print("Starting product groups report generation...")
        
        # Fetch all product groups
        product_groups = self.fetch_product_groups()
        if not product_groups:
            print("No product groups found or API call failed.")
            return ""
        
        print(f"Found {len(product_groups)} product groups")
        
        # Fetch detailed information for each group
        groups_with_details = []
        for group in product_groups:
            group_details = self.fetch_product_group_details(group["id"])
            if group_details:
                # Merge statistics from the list call into the detailed data
                group_details["statistics"] = group.get("statistics", {})
                groups_with_details.append(group_details)
            time.sleep(0.1)  # Small delay to be respectful to the API
        
        # Fetch rule definitions for interpretation
        self.fetch_rule_definitions()
        
        # Generate the report
        report_lines = [
            "# Complete Product Groups Report",
            "",
            f"**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}",
            f"**Total Product Groups:** {len(groups_with_details)}",
            ""
        ]
        
        # Add statistics summary
        report_lines.append(self.generate_statistics_summary(groups_with_details))
        
        # Add summary table
        report_lines.append(self.generate_summary_table(groups_with_details))
        report_lines.append("")
        
        # Add detailed sections
        report_lines.append(self.generate_detailed_sections(groups_with_details))
        
        # Write to file
        report_content = "\n".join(report_lines)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        print(f"Report generated successfully: {output_file}")
        return report_content



"""
Location Groups Reporter
========================

This script fetches location group data from the Kognitiv Loyalty API
and generates a comprehensive markdown report with human-readable interpretations.

Usage:
    python location_groups_reporter.py --token YOUR_JWT_TOKEN

Requirements:
    - requests library (pip install requests)
    - Valid JWT token for the Kognitiv Loyalty API
"""

import json
import requests
import argparse
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

class LocationGroupsReporter(object):
    def __init__(self, token: str, base_url: str = "https://ca.kognitivloyalty.com/api"):
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "api-version": "2025.3",
            "Content-Type": "application/json"
        }
        self.rule_definitions = None
        
    def make_api_call(self, endpoint: str) -> Dict[str, Any]:
        """Make an API call and return the JSON response."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making API call to {endpoint}: {e}")
            return {}
    
    def fetch_location_groups(self) -> List[Dict[str, Any]]:
        """Fetch the list of all location groups with statistics."""
        print("Fetching location groups list...")
        response = self.make_api_call("groups/location?statistics=true")
        return response.get("data", [])
    
    def fetch_location_group_details(self, group_id: int) -> Dict[str, Any]:
        """Fetch detailed information for a specific location group."""
        print(f"Fetching details for location group {group_id}...")
        response = self.make_api_call(f"groups/location/{group_id}")
        return response.get("data", {})
    
    def fetch_rule_definitions(self) -> Dict[str, Any]:
        """Fetch all rule definitions for interpretation."""
        if self.rule_definitions is None:
            print("Fetching rule definitions...")
            self.rule_definitions = self.make_api_call("groups/ruleDefinitions")
        return self.rule_definitions
    
    def get_rule_definition(self, rule_def_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific rule definition by ID."""
        rule_defs = self.fetch_rule_definitions()
        for rule_def in rule_defs.get("data", []):
            if rule_def["id"] == rule_def_id:
                return rule_def
        return None
    
    def get_component_definition(self, rule_def: Dict[str, Any], comp_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific component definition from a rule definition."""
        if rule_def:
            for component in rule_def.get("components", []):
                if component["id"] == comp_id:
                    return component
        return None
    
    def format_date(self, date_str: str) -> str:
        """Format a date string for human readability."""
        if not date_str:
            return "Not specified"
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%B %d, %Y")
        except:
            return date_str
    
    def format_number(self, num: Any) -> str:
        """Format numbers for human readability."""
        if num is None:
            return "0"
        try:
            return f"{int(num):,}"
        except:
            return str(num)
    
    def interpret_operator(self, operator: str) -> str:
        """Convert API operators to human-readable text."""
        operator_map = {
            "isEqual": "equals",
            "isNotEqual": "does not equal",
            "isGreaterThan": "is greater than",
            "isLessThan": "is less than",
            "isGreaterThanOrEqualTo": "is greater than or equal to",
            "isLessThanOrEqualTo": "is less than or equal to",
            "isBetween": "is between",
            "customDates": "custom date range",
            "entireProgram": "entire program period",
            "currentDay": "current day",
            "previousDay": "previous day",
            "currentWeek": "current week",
            "previousWeek": "previous week",
            "currentMonth": "current month",
            "previousMonth": "previous month",
            "currentYear": "current year",
            "previousYear": "previous year"
        }
        return operator_map.get(operator, operator)
    
    def interpret_rule(self, rule: Dict[str, Any]) -> str:
        """Convert a rule object to human-readable text."""
        rule_def_id = rule["ruleDefinition"]["id"]
        rule_def = self.get_rule_definition(rule_def_id)
        
        if not rule_def:
            return f"Unknown rule type (ID: {rule_def_id})"
        
        rule_name = rule_def["name"]
        conditions = []
        
        for value in rule.get("values", []):
            comp_def = self.get_component_definition(rule_def, value["component"]["id"])
            if comp_def:
                label = comp_def["label"]
                operator = self.interpret_operator(value["operator"])
                
                if value.get("selectedText"):
                    condition_value = value["selectedText"]
                elif value.get("value1") and value.get("value2"):
                    condition_value = f"{self.format_date(value['value1'])} to {self.format_date(value['value2'])}"
                elif value.get("value1"):
                    condition_value = value["value1"]
                else:
                    condition_value = "Not specified"
                
                conditions.append(f"{label} {operator} {condition_value}")
        
        if conditions:
            return f"{rule_name}: {' AND '.join(conditions)}"
        else:
            return rule_name
    
    def generate_summary_table(self, groups_with_details: List[Dict[str, Any]]) -> str:
        """Generate the summary table for all location groups."""
        lines = [
            "## Summary",
            "",
            "| ID | Name | Status | Rebuild | Logic | Rules | Members | Last Built |",
            "|----|------|--------|---------|-------|-------|---------|------------|"
        ]
        
        for group in sorted(groups_with_details, key=lambda x: x["id"]):
            rule_count = len(group.get("rules", []))
            member_count = self.format_number(group.get("statistics", {}).get("memberCount", 0))
            last_built = group.get("lastBuiltTimestamp", "").split("T")[0] if group.get("lastBuiltTimestamp") else "Unknown"
            
            lines.append(
                f"| {group['id']} | {group['name']} | {group['status']} | "
                f"{group['rebuildFrequency']} | {group['ruleMatch']} | {rule_count} | {member_count} | {last_built} |"
            )
        
        return "\n".join(lines)
    
    def generate_detailed_sections(self, groups_with_details: List[Dict[str, Any]]) -> str:
        """Generate detailed sections for each location group."""
        lines = [
            "## Detailed Rules for Each Location Group",
            ""
        ]
        
        for group in sorted(groups_with_details, key=lambda x: x["id"]):
            lines.append(f"### {group['name']} (ID: {group['id']})")
            lines.append("")
            lines.append(f"**Status:** {group['status']}")
            
            rule_match_text = "ANY" if group['ruleMatch'] == 'any' else "ALL"
            lines.append(f"**Rule Logic:** {group['ruleMatch']} (member qualifies if they match {rule_match_text} of the rules)")
            lines.append(f"**Rebuild Frequency:** {group['rebuildFrequency']}")
            
            # Add statistics if available
            stats = group.get("statistics", {})
            if stats:
                member_count = self.format_number(stats.get("memberCount", 0))
                lines.append(f"**Member Count:** {member_count}")
                
                if stats.get("lastBuiltTimestamp"):
                    try:
                        last_built = datetime.fromisoformat(stats["lastBuiltTimestamp"].replace('Z', '+00:00'))
                        lines.append(f"**Statistics Last Updated:** {last_built.strftime('%B %d, %Y at %H:%M UTC')}")
                    except:
                        lines.append(f"**Statistics Last Updated:** {stats['lastBuiltTimestamp']}")
            
            if group.get("lastBuiltTimestamp"):
                try:
                    last_built = datetime.fromisoformat(group["lastBuiltTimestamp"].replace('Z', '+00:00'))
                    lines.append(f"**Last Built:** {last_built.strftime('%B %d, %Y at %H:%M UTC')}")
                except:
                    lines.append(f"**Last Built:** {group['lastBuiltTimestamp']}")
            
            rules = group.get("rules", [])
            if rules:
                lines.append("")
                lines.append("**Rules:**")
                for i, rule in enumerate(rules, 1):
                    interpretation = self.interpret_rule(rule)
                    lines.append(f"{i}. {interpretation}")
            else:
                lines.append("")
                lines.append("**Rules:** No specific rules defined (likely uses default criteria)")
            
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_statistics_summary(self, groups_with_details: List[Dict[str, Any]]) -> str:
        """Generate a statistics summary section."""
        lines = [
            "## Statistics Summary",
            ""
        ]
        
        total_members = 0
        active_groups = 0
        daily_groups = 0
        monthly_groups = 0
        manual_groups = 0
        
        for group in groups_with_details:
            stats = group.get("statistics", {})
            member_count = stats.get("memberCount", 0) or 0
            total_members += member_count
            
            if group.get("status") == "valid":
                active_groups += 1
            
            rebuild_freq = group.get("rebuildFrequency", "")
            if rebuild_freq == "daily":
                daily_groups += 1
            elif rebuild_freq == "monthly":
                monthly_groups += 1
            elif rebuild_freq == "manual":
                manual_groups += 1
        
        lines.extend([
            f"**Total Location Groups:** {len(groups_with_details)}",
            f"**Active Groups:** {active_groups}",
            f"**Total Members Across All Groups:** {self.format_number(total_members)}",
            "",
            "**Rebuild Frequency Distribution:**",
            f"- Daily: {daily_groups} groups",
            f"- Monthly: {monthly_groups} groups", 
            f"- Manual: {manual_groups} groups",
            ""
        ])
        
        return "\n".join(lines)
    
    def generate_location_report(self, output_file: str = "location_groups_report.md") -> str:
        """Generate the complete location groups report."""
        print("Starting location groups report generation...")
        
        # Fetch all location groups
        location_groups = self.fetch_location_groups()
        if not location_groups:
            print("No location groups found or API call failed.")
            return ""
        
        print(f"Found {len(location_groups)} location groups")
        
        # Fetch detailed information for each group
        groups_with_details = []
        for group in location_groups:
            group_details = self.fetch_location_group_details(group["id"])
            if group_details:
                # Merge statistics from the list call into the detailed data
                group_details["statistics"] = group.get("statistics", {})
                groups_with_details.append(group_details)
            time.sleep(0.1)  # Small delay to be respectful to the API
        
        # Fetch rule definitions for interpretation
        self.fetch_rule_definitions()
        
        # Generate the report
        report_lines = [
            "# Complete Location Groups Report",
            "",
            f"**Generated:** {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}",
            f"**Total Location Groups:** {len(groups_with_details)}",
            ""
        ]
        
        # Add statistics summary
        report_lines.append(self.generate_statistics_summary(groups_with_details))
        
        # Add summary table
        report_lines.append(self.generate_summary_table(groups_with_details))
        report_lines.append("")
        
        # Add detailed sections
        report_lines.append(self.generate_detailed_sections(groups_with_details))
        
        # Write to file
        report_content = "\n".join(report_lines)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        print(f"Report generated successfully: {output_file}")
        return report_content




# ----

import os
import uuid
import logging
from logging.handlers import RotatingFileHandler
import boto3
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent
from strands import tool
from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider
# from location_groups_reporter import LocationGroupsReporter

# --------------------------
# Logging Configuration
# --------------------------
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "agent_app.log")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# File handler with rotation (max 5 MB per file, keep 5 backups)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=5)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
file_handler.setFormatter(file_formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s")
console_handler.setFormatter(console_formatter)

# Root logger
logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])
logger = logging.getLogger(__name__)

# S3 Configuration
S3_BUCKET = os.environ.get("S3_BUCKET", "loyalty-reports-bucket")
S3_PREFIX = os.environ.get("S3_PREFIX", "reports/")

# Global token
TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjlBMEI0RjRCNDE2MDUwMjMzMTgwN0RGOTU1RTNDQ0IyMDM2MkI0MzYiLCJ0eXAiOiJKV1QiLCJ4NXQiOiJtZ3RQUzBGZ1VDTXhnSDM1VmVQTXNnTml0RFkifQ.eyJuYmYiOjE3NTgzMDgxOTAsImV4cCI6MTc1ODMxMTc5MCwiaXNzIjoiaHR0cHM6Ly9jYS5rb2duaXRpdmxveWFsdHkuY29tL2F1dGgiLCJhdWQiOlsiaHR0cHM6Ly9jYS5rb2duaXRpdmxveWFsdHkuY29tL2F1dGgvcmVzb3VyY2VzIiwiQWltaWFTYWFTX0FQSSJdLCJjbGllbnRfaWQiOiJhcHBfc3BhIiwic3ViIjoiMzJmZWQ3MjItZmZiZi00ZGRjLTg4NzktMjUwODMxMTQ5ZjY0IiwiYXV0aF90aW1lIjoxNzU4MzA4MTc3LCJpZHAiOiJLb2duaXRpdkF6dXJlQUQiLCJjdXN0b21lcl9pZCI6IjEwODQiLCJzY29wZSI6WyJvcGVuaWQiLCJwcm9maWxlIiwiY3VzdG9tZXIiLCJjb3JlX2lkZW50aXR5IiwiQWltaWFTYWFTX0FQSSJdLCJhbXIiOlsiZXh0ZXJuYWwiXX0.n2I0DcC4hCv54skVcpDrr7jRMTNNPEDjBYeOOi5G7dKxrsMPKsyk6FQnMQYe6ttJlIUH34fNTE1srLS4piy9HmUkOUd_6STuHQbM2m8LYPewQdyK-4y58yxfPVAPjhOm-gDrfE0wzBGkEdSMZA4EhAdmxYGwVnJcfqr2dgAs8GMiVFP0MYeYD-tG2KG3rZ9LnSkSREC0Ra6EturH6nmpDuClyC-oDeGxiSsT2O81Y5TmL1M7dyQpAGNj3gFreQgwOZ00h_Qt9j1DjChsdFwsVHqi9h2uZGOZHM9aaxM4TIx9MsZQQosjfaQucuH4KmbVxmeDewe7VzL2ym05nkrWBg"
BASE_URL = "https://ca.kognitivloyalty.com/api"

def upload_to_s3(file_path, s3_key):
    """Upload a file to S3 bucket"""
    try:
        s3_client = boto3.client('s3')
        
        # Check if bucket exists, create if it doesn't
        try:
            s3_client.head_bucket(Bucket=S3_BUCKET)
        except s3_client.exceptions.NoSuchBucket:
            s3_client.create_bucket(Bucket=S3_BUCKET)
            logger.info(f"Created S3 bucket: {S3_BUCKET}")
        
        s3_client.upload_file(file_path, S3_BUCKET, s3_key)
        s3_url = f"s3://{S3_BUCKET}/{s3_key}"
        logger.info(f"File uploaded to S3: {s3_url}")
        return s3_url
    except Exception as e:
        logger.error(f"Failed to upload to S3: {e}")
        return None

# Initialize the AgentCore application
app = BedrockAgentCoreApp()

# --- Memory Configuration ---
MEMORY_ID = "123"  # os.environ.get("AGENTCORE_MEMORY_ID")
if not MEMORY_ID:
    raise ValueError("Please set the AGENTCORE_MEMORY_ID environment variable.")

logger.info("Starting application with MEMORY_ID=%s", MEMORY_ID)


# Define a tool with the decorator
# @tool
# def generate_report():
#     """Generate a report of the location groups"""
#     logger.debug("generate_report tool invoked")
#     try:
#         token = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjlBMEI0RjRCNDE2MDUwMjMzMTgwN0RGOTU1RTNDQ0IyMDM2MkI0MzYiLCJ0eXAiOiJKV1QiLCJ4NXQiOiJtZ3RQUzBGZ1VDTXhnSDM1VmVQTXNnTml0RFkifQ.eyJuYmYiOjE3NTgyOTA4MjMsImV4cCI6MTc1ODI5NDQyMywiaXNzIjoiaHR0cHM6Ly9jYS5rb2duaXRpdmxveWFsdHkuY29tL2F1dGgiLCJhdWQiOlsiaHR0cHM6Ly9jYS5rb2duaXRpdmxveWFsdHkuY29tL2F1dGgvcmVzb3VyY2VzIiwiQWltaWFTYWFTX0FQSSJdLCJjbGllbnRfaWQiOiJhcHBfc3BhIiwic3ViIjoiMzJmZWQ3MjItZmZiZi00ZGRjLTg4NzktMjUwODMxMTQ5ZjY0IiwiYXV0aF90aW1lIjoxNzU4MjkwODA3LCJpZHAiOiJLb2duaXRpdkF6dXJlQUQiLCJjdXN0b21lcl9pZCI6IjEwODQiLCJzY29wZSI6WyJvcGVuaWQiLCJwcm9maWxlIiwiY3VzdG9tZXIiLCJjb3JlX2lkZW50aXR5IiwiQWltaWFTYWFTX0FQSSJdLCJhbXIiOlsiZXh0ZXJuYWwiXX0.pTAzQR1yQOJe9QdBiBBbGir3LDettaV38hcDi395YFHp7cOLVwjYJtUIbidGN4Dp0AfmiLmxpMMGlsqjkzcfa647hhy590_grOsAn6oHEo7vm-Qm5Fry_swoa5JQm_ImxNumx_qFRwzTpCBeAJ1f4U1QWnIDRGzs3IZ8QGmYcI9I778S3OGwyVbosmvjmDl6s4CQMTMNxhJVgD-0wYxDTZ0UGl69hK-KotowBRitcIGKtwfsdSPa-NwhfmRl_g_e6ZkeTUA1ibde3IWenPHQNWKHOzQv2ef70PUqp2SdrjSOIRLPQApm7mgFb_hG_ZGZ7naX1AmlIr1E8LobqYm2Cg"
#         output = "location_groups_report.md"
#         base_url = "https://ca.kognitivloyalty.com/api"
#         result = LocationGroupsReporter(token, base_url).generate_report(output)
#         logger.info("generate_report tool executed successfully")
#         return result
#     except Exception as e:
#         logger.exception("Error while generating report")
#         return {"error": str(e)}

@tool
def generate_reward_group_report():
    """Generate a report of the tier groups"""
    logger.debug("generate_report tool invoked")
    output = "tier_report.md"
    
    try:
        reporter = RewardGroupsReporterFixed(TOKEN, BASE_URL)
        reporter.generate_reward_group_report(output)
        
        # Upload to S3
        s3_key = f"{S3_PREFIX}reward_groups/{output}"
        s3_url = upload_to_s3(output, s3_key)
        
        if s3_url:
            return f"Report generated and uploaded to S3: {s3_url}"
        else:
            return f"Report generated locally: {output}"
    except Exception as e:
        print(f"Error generating report: {e}")
        return 1



@tool
def generate_tier_report():
    """Generate a report of the tier groups"""
    logger.debug("generate_report tool invoked")
    output = "tier_report.md"
    
    try:
        reporter = TiersReporter(TOKEN, BASE_URL)
        reporter.generate_tier_report(output)
        
        # Upload to S3
        s3_key = f"{S3_PREFIX}tiers/{output}"
        s3_url = upload_to_s3(output, s3_key)
        
        if s3_url:
            return f"Report generated and uploaded to S3: {s3_url}"
        else:
            return f"Report generated locally: {output}"
    except Exception as e:
        print(f"Error generating report: {e}")
        return 1

@tool
def generate_location_report():
    """Generate a report of the location groups"""
    logger.debug("generate_report tool invoked")
    output = "location_groups_report.md"
    
    try:
        reporter = LocationGroupsReporter(TOKEN, BASE_URL)
        reporter.generate_location_report(output)
        
        # Upload to S3
        s3_key = f"{S3_PREFIX}location_groups/{output}"
        s3_url = upload_to_s3(output, s3_key)
        
        if s3_url:
            return f"Report generated and uploaded to S3: {s3_url}"
        else:
            return f"Report generated locally: {output}"
    except Exception as e:
        print(f"Error generating report: {e}")
        return 1

@tool
def generate_product_report():
    """Generate a report of the product groups"""
    logger.debug("generate_report tool invoked")
    output = "product_group_report.md"
    
    try:
        reporter = ProductGroupsReporter(TOKEN, BASE_URL)
        reporter.generate_product_report(output)
        
        # Upload to S3
        s3_key = f"{S3_PREFIX}product_groups/{output}"
        s3_url = upload_to_s3(output, s3_key)
        
        if s3_url:
            return f"Report generated and uploaded to S3: {s3_url}"
        else:
            return f"Report generated locally: {output}"
    except Exception as e:
        print(f"Error generating report: {e}")
        return 1

@tool
def generate_audience_report():
    """Generate a report of the audience groups"""
    logger.debug("generate_report tool invoked")
    output = "audience_groups_report.md"
    
    try:
        reporter = AudienceGroupsReporter(TOKEN, BASE_URL)
        reporter.generate_audience_report(output)
        
        # Upload to S3
        s3_key = f"{S3_PREFIX}audience_groups/{output}"
        s3_url = upload_to_s3(output, s3_key)
        
        if s3_url:
            return f"Report generated and uploaded to S3: {s3_url}"
        else:
            return f"Report generated locally: {output}"
    except Exception as e:
        print(f"Error generating report: {e}")
        return 1

@tool
def generate_promotion_report():
    """Generate a report of the audience groups"""
    logger.debug("generate_report tool invoked")
    output = "promotion_report.md"
    
    try:
        reporter = PromotionsReporterFinal(TOKEN, BASE_URL)
        reporter.generate_promotion_report(output)
        
        # Upload to S3
        s3_key = f"{S3_PREFIX}promotions/{output}"
        s3_url = upload_to_s3(output, s3_key)
        
        if s3_url:
            return f"Report generated and uploaded to S3: {s3_url}"
        else:
            return f"Report generated locally: {output}"
    except Exception as e:
        print(f"Error generating report: {e}")
        return 1

@tool
def generate_reward_report():
    """Generate a report of the reward groups"""
    logger.debug("generate_report tool invoked")
    output = "reward_report.md"
    
    try:
        reporter = RewardsReporter(TOKEN, BASE_URL)
        reporter.generate_reward_report(output)
        
        # Upload to S3
        s3_key = f"{S3_PREFIX}rewards/{output}"
        s3_url = upload_to_s3(output, s3_key)
        
        if s3_url:
            return f"Report generated and uploaded to S3: {s3_url}"
        else:
            return f"Report generated locally: {output}"
    except Exception as e:
        print(f"Error generating report: {e}")
        return 1


@app.entrypoint
def invoke(payload, context):
    logger.info("invoke() called with payload=%s", payload)

    user_message = payload.get("prompt")
    actor_id = payload.get("actorId", "default-user")
    session_id = payload.get("sessionId", str(uuid.uuid4()))

    logger.debug("Extracted user_message=%s, actor_id=%s, session_id=%s",
                 user_message, actor_id, session_id)

    if not user_message:
        logger.warning("No prompt provided in payload")
        return {"result": "No prompt provided."}

    try:
        # --- Initialize the memory tool provider with the required namespace ---
        memory_provider = AgentCoreMemoryToolProvider(
            memory_id=MEMORY_ID,
            actor_id=actor_id,
            session_id=session_id,
            namespace=f"/actors/{actor_id}/conversations",
        )
        logger.info("Memory provider initialized for actor_id=%s", actor_id)

        # --- Initialize the Agent with the Claude model and the memory + report tool ---
        agent = Agent(
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            tools=[memory_provider.tools[0], generate_location_report,generate_product_report,generate_audience_report, generate_promotion_report, generate_reward_report, generate_tier_report, generate_reward_group_report]
            
        )
        logger.info("Agent initialized with model and tools")

        result = agent(user_message)
        logger.debug("Agent result=%s", result)

        return {
            "result": result.message,
            "sessionId": session_id,
            "actorId": actor_id,
        }

    except Exception as e:
        logger.exception("Error during invoke() execution")
        return {
            "error": str(e),
            "sessionId": session_id,
            "actorId": actor_id,
        }


if __name__ == "__main__":
    os.environ["AGENTCORE_MEMORY_ID"] = "your-memory-id"
    logger.info("Running app in __main__ mode")
    app.run()
