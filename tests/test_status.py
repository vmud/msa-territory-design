"""Smoke tests for status calculation module"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from src.shared.status import get_retailer_status, get_all_retailers_status


class TestStatusCalculation:
    """Tests for status calculation functions"""
    
    def test_get_retailer_status_returns_dict(self):
        """Test that get_retailer_status returns a dictionary"""
        status = get_retailer_status('verizon')
        assert isinstance(status, dict)
    
    def test_get_retailer_status_has_required_fields(self):
        """Test that status dict contains required fields"""
        status = get_retailer_status('verizon')
        required_fields = ['name', 'status', 'progress', 'stores_scraped', 'duration', 'phases']
        for field in required_fields:
            assert field in status, f"Missing required field: {field}"
    
    def test_get_retailer_status_invalid_retailer(self):
        """Test that invalid retailer raises ValueError"""
        with pytest.raises(ValueError, match="Invalid retailer"):
            get_retailer_status('invalid_retailer')
    
    def test_get_all_retailers_status_returns_dict(self):
        """Test that get_all_retailers_status returns a dictionary"""
        status = get_all_retailers_status()
        assert isinstance(status, dict)
    
    def test_get_all_retailers_status_has_retailers_and_global(self):
        """Test that all status contains retailers and global sections"""
        status = get_all_retailers_status()
        assert 'retailers' in status
        assert 'global' in status
        assert isinstance(status['retailers'], dict)
        assert isinstance(status['global'], dict)
    
    def test_get_all_retailers_status_contains_all_retailers(self):
        """Test that all 6 retailers are present"""
        status = get_all_retailers_status()
        retailers = status['retailers']
        expected_retailers = ['verizon', 'att', 'target', 'tmobile', 'walmart', 'bestbuy']
        for retailer in expected_retailers:
            assert retailer in retailers, f"Missing retailer: {retailer}"
    
    def test_get_all_retailers_status_global_stats(self):
        """Test that global stats contain expected fields"""
        status = get_all_retailers_status()
        global_stats = status['global']
        expected_fields = ['total_stores', 'active_scrapers', 'overall_progress', 'est_remaining']
        for field in expected_fields:
            assert field in global_stats, f"Missing global field: {field}"
    
    def test_retailer_status_disabled(self):
        """Test that disabled retailers have status 'disabled'"""
        status = get_retailer_status('bestbuy')
        assert status['status'] == 'disabled'
    
    def test_retailer_status_progress_range(self):
        """Test that progress is between 0 and 100"""
        status = get_retailer_status('verizon')
        assert 0 <= status['progress'] <= 100
    
    def test_retailer_status_stores_scraped_non_negative(self):
        """Test that stores_scraped is non-negative"""
        status = get_retailer_status('verizon')
        assert status['stores_scraped'] >= 0
    
    def test_html_crawl_phases(self):
        """Test that html_crawl retailers have 4 phases"""
        status = get_retailer_status('verizon')
        assert len(status['phases']) == 4
        expected_phases = ['states', 'cities', 'urls', 'extract']
        for i, phase_name in enumerate(expected_phases):
            assert status['phases'][i]['name'] == phase_name
    
    def test_sitemap_phases(self):
        """Test that sitemap retailers have 2 phases"""
        status = get_retailer_status('target')
        assert len(status['phases']) == 2
        expected_phases = ['sitemap', 'extract']
        for i, phase_name in enumerate(expected_phases):
            assert status['phases'][i]['name'] == phase_name
    
    def test_phase_status_values(self):
        """Test that phase status is one of: pending, active, complete"""
        status = get_retailer_status('verizon')
        valid_statuses = ['pending', 'active', 'complete']
        for phase in status['phases']:
            assert phase['status'] in valid_statuses
    
    @patch('src.shared.status.get_checkpoint_path')
    def test_get_retailer_status_with_no_checkpoint(self, mock_checkpoint_path):
        """Test status calculation when no checkpoint exists"""
        mock_checkpoint_path.return_value = Path('/nonexistent/checkpoint.json')
        status = get_retailer_status('verizon')
        assert status['status'] in ['pending', 'disabled']
        assert status['progress'] == 0
