"""
Unit tests for the extractor interfaces.

These tests verify that implementations of the extractor interfaces
properly adhere to the required contract.
"""

import pytest
import abc
from urllib.parse import urlparse
from typing import Dict, List, Optional, Any

from src.extractors.interfaces import IContentExtractor, ILinkExtractor


class TestIContentExtractor:
    """Tests for the IContentExtractor interface."""
    
    def test_interface_cannot_be_instantiated(self):
        """Test that IContentExtractor cannot be instantiated directly."""
        with pytest.raises(TypeError):
            IContentExtractor()
    
    def test_abstract_methods_defined(self):
        """Test that IContentExtractor defines the required abstract methods."""
        # Check that abstract methods are defined
        assert hasattr(IContentExtractor, 'extract')
        assert hasattr(IContentExtractor, 'get_priority_selectors')
        
        # Check that they're marked as abstract
        assert IContentExtractor.extract.__isabstractmethod__
        assert IContentExtractor.get_priority_selectors.__isabstractmethod__
    
    def test_implementation_requirements(self):
        """Test that implementations must override abstract methods."""
        # Create an incomplete implementation that doesn't override all methods
        class IncompleteExtractor(IContentExtractor):
            pass
        
        # Should not be able to instantiate it
        with pytest.raises(TypeError):
            IncompleteExtractor()
        
        # Create a complete implementation
        class CompleteExtractor(IContentExtractor):
            async def extract(self, html, url, context=None):
                return {"success": True}
            
            def get_priority_selectors(self):
                return ["main", "article"]
        
        # Should be able to instantiate it
        extractor = CompleteExtractor()
        assert isinstance(extractor, IContentExtractor)


class TestILinkExtractor:
    """Tests for the ILinkExtractor interface."""
    
    def test_interface_cannot_be_instantiated(self):
        """Test that ILinkExtractor cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ILinkExtractor()
    
    def test_abstract_methods_defined(self):
        """Test that ILinkExtractor defines the required abstract methods."""
        # Check that abstract methods are defined
        assert hasattr(ILinkExtractor, 'extract')
        assert hasattr(ILinkExtractor, 'get_navigation_selectors')
        assert hasattr(ILinkExtractor, 'should_follow_link')
        
        # Check that they're marked as abstract
        assert ILinkExtractor.extract.__isabstractmethod__
        assert ILinkExtractor.get_navigation_selectors.__isabstractmethod__
        assert ILinkExtractor.should_follow_link.__isabstractmethod__
    
    def test_implementation_requirements(self):
        """Test that implementations must override abstract methods."""
        # Create an incomplete implementation that doesn't override all methods
        class IncompleteExtractor(ILinkExtractor):
            async def extract(self, html, base_url, context=None):
                return []
        
        # Should not be able to instantiate it
        with pytest.raises(TypeError):
            IncompleteExtractor()
        
        # Create a complete implementation
        class CompleteExtractor(ILinkExtractor):
            async def extract(self, html, base_url, context=None):
                return []
            
            def get_navigation_selectors(self):
                return ["nav", ".sidebar"]
            
            def should_follow_link(self, link_url, current_url, link_text):
                return True
        
        # Should be able to instantiate it
        extractor = CompleteExtractor()
        assert isinstance(extractor, ILinkExtractor)


class TestInterfaceUsage:
    """Tests for using the interfaces in practical scenarios."""
    
    @pytest.mark.asyncio
    async def test_content_extractor_contract(self):
        """Test that a content extractor implementation fulfills the contract."""
        class SimpleContentExtractor(IContentExtractor):
            async def extract(self, html, url, context=None):
                return {
                    "title": "Test Page",
                    "content": "Test content",
                    "metadata": {"keywords": ["test"]},
                    "elements": {"headings": ["Test"]},
                    "success": True,
                    "extraction_method": "test_method"
                }
            
            def get_priority_selectors(self):
                return ["main", "article"]
                
        extractor = SimpleContentExtractor()
        result = await extractor.extract("<html></html>", urlparse("https://example.com"), {})
        
        # Verify that the result contains all required keys
        required_keys = ["title", "content", "metadata", "elements", "success", "extraction_method"]
        for key in required_keys:
            assert key in result
    
    @pytest.mark.asyncio
    async def test_link_extractor_contract(self):
        """Test that a link extractor implementation fulfills the contract."""
        class SimpleLinkExtractor(ILinkExtractor):
            async def extract(self, html, base_url, context=None):
                return [{
                    "url": "https://example.com/docs",
                    "text": "Documentation",
                    "type": "navigation",
                    "priority": 1,
                    "depth": 0
                }]
            
            def get_navigation_selectors(self):
                return ["nav", ".sidebar"]
                
            def should_follow_link(self, link_url, current_url, link_text):
                return True
                
        extractor = SimpleLinkExtractor()
        result = await extractor.extract("<html></html>", urlparse("https://example.com"), {})
        
        # Verify that the result is a list and entries contain all required keys
        assert isinstance(result, list)
        if result:
            required_keys = ["url", "text", "type", "priority", "depth"]
            for key in required_keys:
                assert key in result[0]
