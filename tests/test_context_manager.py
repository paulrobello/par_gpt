"""Tests for the thread-safe context manager."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from par_gpt.utils.context_manager import ThreadSafeContextManager, get_context_manager


class TestThreadSafeContextManager:
    """Test cases for ThreadSafeContextManager."""

    def test_basic_set_get(self):
        """Test basic set and get operations."""
        manager = ThreadSafeContextManager()
        
        manager.set_context(test_key="test_value", debug=True)
        
        assert manager.get_context("test_key") == "test_value"
        assert manager.get_context("debug") is True
        assert manager.get_context("nonexistent") is None
        assert manager.get_context("nonexistent", "default") == "default"

    def test_clear_context(self):
        """Test clearing context."""
        manager = ThreadSafeContextManager()
        
        manager.set_context(key1="value1", key2="value2")
        assert manager.get_context("key1") == "value1"
        
        manager.clear_context()
        assert manager.get_context("key1") is None
        assert manager.get_context("key2") is None

    def test_context_scope(self):
        """Test context scope manager."""
        manager = ThreadSafeContextManager()
        
        # Set initial context
        manager.set_context(existing="original")
        
        with manager.context_scope(temp="temporary", existing="overridden"):
            assert manager.get_context("temp") == "temporary"
            assert manager.get_context("existing") == "overridden"
        
        # After scope, temporary value should be gone, original restored
        assert manager.get_context("temp") is None
        assert manager.get_context("existing") == "original"

    def test_yes_to_all_enabled(self):
        """Test yes_to_all_enabled convenience method."""
        manager = ThreadSafeContextManager()
        
        assert manager.is_yes_to_all_enabled() is False
        
        manager.set_context(yes_to_all=True)
        assert manager.is_yes_to_all_enabled() is True

    def test_thread_isolation(self):
        """Test that contexts are isolated between threads."""
        manager = ThreadSafeContextManager()
        results = {}
        
        def thread_worker(thread_id: int):
            # Each thread sets its own context
            manager.set_context(thread_id=thread_id, value=f"thread_{thread_id}")
            
            # Small delay to allow other threads to set their context
            time.sleep(0.01)
            
            # Each thread should only see its own context
            results[thread_id] = {
                "thread_id": manager.get_context("thread_id"),
                "value": manager.get_context("value"),
            }
        
        # Run multiple threads concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(thread_worker, i) for i in range(5)]
            for future in as_completed(futures):
                future.result()  # Wait for completion
        
        # Verify each thread had its own isolated context
        for i in range(5):
            assert results[i]["thread_id"] == i
            assert results[i]["value"] == f"thread_{i}"

    def test_concurrent_access(self):
        """Test concurrent access to the same context manager."""
        manager = ThreadSafeContextManager()
        errors = []
        
        def concurrent_operations(thread_id: int):
            try:
                for i in range(100):
                    # Set, get, and clear operations
                    manager.set_context(counter=i, thread=thread_id)
                    value = manager.get_context("counter")
                    assert value == i
                    
                    # Use context scope
                    with manager.context_scope(temp=f"temp_{i}"):
                        temp_value = manager.get_context("temp")
                        assert temp_value == f"temp_{i}"
                
                manager.clear_context()
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")
        
        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(concurrent_operations, i) for i in range(10)]
            for future in as_completed(futures):
                future.result()
        
        # Should have no errors
        assert len(errors) == 0, f"Concurrent access errors: {errors}"

    def test_global_instance_functions(self):
        """Test the global instance convenience functions."""
        from par_gpt.utils.context_manager import (
            clear_tool_context,
            get_tool_context,
            is_yes_to_all_enabled,
            set_tool_context,
        )
        
        # Clear any existing context
        clear_tool_context()
        
        set_tool_context(test="global", yes_to_all=True)
        
        assert get_tool_context("test") == "global"
        assert is_yes_to_all_enabled() is True
        
        clear_tool_context()
        assert get_tool_context("test") is None

    def test_backward_compatibility(self):
        """Test backward compatibility with tool_context module."""
        from par_gpt.tool_context import (
            clear_tool_context,
            get_tool_context,
            is_yes_to_all_enabled,
            set_tool_context,
        )
        
        # Clear any existing context
        clear_tool_context()
        
        set_tool_context(compat="test", yes_to_all=False)
        
        assert get_tool_context("compat") == "test"
        assert is_yes_to_all_enabled() is False
        
        set_tool_context(yes_to_all=True)
        assert is_yes_to_all_enabled() is True
        
        clear_tool_context()
        assert get_tool_context("compat") is None

    def test_context_manager_singleton(self):
        """Test that get_context_manager returns the same instance."""
        manager1 = get_context_manager()
        manager2 = get_context_manager()
        
        assert manager1 is manager2
        
        # Setting context on one should affect the other
        manager1.set_context(test="singleton")
        assert manager2.get_context("test") == "singleton"

    def test_get_all_context(self):
        """Test getting all context values."""
        manager = ThreadSafeContextManager()
        
        test_context = {"key1": "value1", "key2": "value2", "debug": True}
        manager.set_context(**test_context)
        
        all_context = manager.get_all_context()
        assert all_context == test_context
        
        # Verify it's a copy (modifying returned dict shouldn't affect manager)
        all_context["new_key"] = "new_value"
        assert manager.get_context("new_key") is None

    def test_nested_context_scope(self):
        """Test nested context scopes."""
        manager = ThreadSafeContextManager()
        
        manager.set_context(base="original")
        
        with manager.context_scope(level1="first"):
            assert manager.get_context("base") == "original"
            assert manager.get_context("level1") == "first"
            
            with manager.context_scope(level2="second", base="overridden"):
                assert manager.get_context("base") == "overridden"
                assert manager.get_context("level1") == "first"
                assert manager.get_context("level2") == "second"
            
            # After inner scope
            assert manager.get_context("base") == "original"
            assert manager.get_context("level1") == "first"
            assert manager.get_context("level2") is None
        
        # After outer scope
        assert manager.get_context("base") == "original"
        assert manager.get_context("level1") is None