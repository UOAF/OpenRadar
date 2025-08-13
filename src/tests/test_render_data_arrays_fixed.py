"""
Comprehensive test suite for render_data_arrays.py

Tests the Array of Structs (AoS) render data implementations for GPU-optimized rendering,
including IconRenderData and BaseRenderData functionality.
"""

import pytest
import numpy as np
from unittest.mock import Mock
from typing import Optional

# Import the modules under test
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from render_data_arrays import BaseRenderData, IconRenderData, VelocityVectorRenderData, LockLineRenderData, LineRenderData, PolygonRenderData, TrackRenderDataArrays
from game_object import GameObject
from game_object_types import GameObjectType
from draw.shapes import Shapes


class MockRenderData(BaseRenderData):
    """Mock implementation of BaseRenderData for testing abstract base class functionality."""

    def _get_dtype(self):
        return np.dtype([('test_field', np.float32), ('another_field', np.int32)])

    def _initialize_array(self, capacity: int):
        self.capacity = capacity
        self.data = np.zeros(capacity, dtype=self._get_dtype())

    def _update_object_data(self, index: int, game_obj: GameObject):
        """Mock implementation for abstract method."""
        if self.data is not None:
            self.data[index]['test_field'] = game_obj.U  # Use position as test data
            self.data[index]['another_field'] = 42


class TestBaseRenderData:
    """Test suite for BaseRenderData abstract base class."""

    def test_initialization(self):
        """Test BaseRenderData initialization."""
        mock_render_data = MockRenderData(100)

        assert mock_render_data.capacity == 100
        assert mock_render_data.count == 0
        assert isinstance(mock_render_data.id_to_index, dict)
        assert isinstance(mock_render_data.index_to_id, dict)
        assert len(mock_render_data.id_to_index) == 0
        assert len(mock_render_data.index_to_id) == 0
        assert mock_render_data.data is not None
        assert len(mock_render_data.data) == 100

    def test_resize_increases_capacity(self):
        """Test that resize increases array capacity."""
        mock_render_data = MockRenderData(10)

        # Add some test data
        if mock_render_data.data is not None:
            mock_render_data.data[0]['test_field'] = 1.5
            mock_render_data.data[1]['another_field'] = 42
        mock_render_data.count = 2

        # Resize to larger capacity
        mock_render_data.resize(20)

        assert mock_render_data.capacity == 20
        if mock_render_data.data is not None:
            assert len(mock_render_data.data) == 20
            # Check that existing data is preserved
            assert mock_render_data.data[0]['test_field'] == 1.5
            assert mock_render_data.data[1]['another_field'] == 42

    def test_resize_no_change_when_smaller(self):
        """Test that resize doesn't change capacity when new capacity is smaller."""
        mock_render_data = MockRenderData(100)
        original_capacity = mock_render_data.capacity

        mock_render_data.resize(50)

        assert mock_render_data.capacity == original_capacity

    def test_get_free_index(self):
        """Test getting free index returns correct index."""
        mock_render_data = MockRenderData(10)

        # Should return 0 initially
        index = mock_render_data._get_free_index()
        assert index == 0

        # Simulate adding some objects
        mock_render_data.count = 3
        index = mock_render_data._get_free_index()
        assert index == 3

    def test_get_free_index_auto_resize(self):
        """Test that get_free_index auto-resizes when capacity is reached."""
        mock_render_data = MockRenderData(2)
        mock_render_data.count = 2  # At capacity

        index = mock_render_data._get_free_index()

        assert index == 2
        assert mock_render_data.capacity == 4  # Should have doubled

    def test_remove_by_swap_single_element(self):
        """Test removing the only element."""
        mock_render_data = MockRenderData(10)

        # Add one element
        mock_render_data.count = 1
        mock_render_data.id_to_index["obj1"] = 0
        mock_render_data.index_to_id[0] = "obj1"
        if mock_render_data.data is not None:
            mock_render_data.data[0]['test_field'] = 1.0

        # Remove it
        mock_render_data._remove_by_swap(0, "obj1")

        assert mock_render_data.count == 0
        assert len(mock_render_data.id_to_index) == 0
        assert len(mock_render_data.index_to_id) == 0

    def test_remove_by_swap_multiple_elements(self):
        """Test removing element from middle of array using swap-with-last."""
        mock_render_data = MockRenderData(10)

        # Add three elements
        mock_render_data.count = 3
        for i in range(3):
            obj_id = f"obj{i}"
            mock_render_data.id_to_index[obj_id] = i
            mock_render_data.index_to_id[i] = obj_id
            if mock_render_data.data is not None:
                mock_render_data.data[i]['test_field'] = float(i * 10)
                mock_render_data.data[i]['another_field'] = i * 100

        # Remove middle element (obj1 at index 1)
        mock_render_data._remove_by_swap(1, "obj1")

        assert mock_render_data.count == 2
        # obj2 should now be at index 1 (swapped from index 2)
        assert mock_render_data.id_to_index["obj2"] == 1
        assert mock_render_data.index_to_id[1] == "obj2"
        if mock_render_data.data is not None:
            assert mock_render_data.data[1]['test_field'] == 20.0  # obj2's original value
            assert mock_render_data.data[1]['another_field'] == 200
        # obj1 should be removed from mappings
        assert "obj1" not in mock_render_data.id_to_index
        assert 2 not in mock_render_data.index_to_id  # old index of obj2

    def test_remove_by_swap_last_element(self):
        """Test removing the last element."""
        mock_render_data = MockRenderData(10)

        # Add two elements
        mock_render_data.count = 2
        mock_render_data.id_to_index["obj0"] = 0
        mock_render_data.index_to_id[0] = "obj0"
        mock_render_data.id_to_index["obj1"] = 1
        mock_render_data.index_to_id[1] = "obj1"

        # Remove last element
        mock_render_data._remove_by_swap(1, "obj1")

        assert mock_render_data.count == 1
        assert "obj1" not in mock_render_data.id_to_index
        assert 1 not in mock_render_data.index_to_id
        # obj0 should still be at index 0
        assert mock_render_data.id_to_index["obj0"] == 0
        assert mock_render_data.index_to_id[0] == "obj0"

    def test_remove_by_swap_invalid_index(self):
        """Test that remove_by_swap raises IndexError for invalid indices."""
        mock_render_data = MockRenderData(10)
        mock_render_data.count = 2

        # Test index >= count
        with pytest.raises(IndexError, match="Index out of bounds or empty array"):
            mock_render_data._remove_by_swap(2, "obj")

        # Test empty array
        mock_render_data.count = 0
        with pytest.raises(IndexError, match="Index out of bounds or empty array"):
            mock_render_data._remove_by_swap(0, "obj")

    def test_get_active_data_empty(self):
        """Test get_active_data returns None when array is empty."""
        mock_render_data = MockRenderData(10)

        result = mock_render_data.get_active_data()
        assert result is None

    def test_get_active_data_with_elements(self):
        """Test get_active_data returns correct slice of array."""
        mock_render_data = MockRenderData(10)
        mock_render_data.count = 3

        # Fill some test data
        if mock_render_data.data is not None:
            for i in range(3):
                mock_render_data.data[i]['test_field'] = float(i)

        active_data = mock_render_data.get_active_data()

        assert active_data is not None
        assert len(active_data) == 3
        assert active_data[0]['test_field'] == 0.0
        assert active_data[1]['test_field'] == 1.0
        assert active_data[2]['test_field'] == 2.0


class TestIconRenderData:
    """Test suite for IconRenderData class."""

    def create_mock_game_object(self,
                                object_id: str,
                                u: float = 0.0,
                                v: float = 0.0,
                                color_rgba: tuple = (255, 255, 255, 255),
                                override_color: Optional[tuple] = None) -> Mock:
        """Create a mock GameObject for testing."""
        mock_obj = Mock(spec=GameObject)
        mock_obj.object_id = object_id
        mock_obj.U = u
        mock_obj.V = v
        mock_obj.color_rgba = color_rgba
        mock_obj.override_color = override_color
        return mock_obj

    def test_initialization(self):
        """Test IconRenderData initialization."""
        icon_data = IconRenderData(100)

        assert icon_data.capacity == 100
        assert icon_data.count == 0
        assert icon_data.data is not None
        assert len(icon_data.data) == 100

        # Check dtype structure
        expected_fields = ['position', 'scale', '_buffer', 'color']
        if icon_data.data is not None and icon_data.data.dtype.names is not None:
            assert all(field in icon_data.data.dtype.names for field in expected_fields)

    def test_dtype_structure(self):
        """Test that the numpy dtype has correct structure."""
        icon_data = IconRenderData(10)
        dtype = icon_data._get_dtype()

        assert dtype.names == ('position', 'scale', '_buffer', 'color')
        assert dtype['position'].shape == (2, )  # x, y coordinates
        assert dtype['color'].shape == (4, )  # RGBA values
        assert dtype['scale'].shape == ()  # scalar value
        assert dtype['_buffer'].shape == ()  # padding scalar
        # Check that the fields use float32 by creating an array and checking element type
        test_array = np.zeros(1, dtype=dtype)
        assert test_array['position'].dtype == np.float32
        assert test_array['color'].dtype == np.float32
        assert test_array['scale'].dtype == np.float32

    def test_add_object(self):
        """Test adding a game object to the icon array."""
        icon_data = IconRenderData(10)
        mock_obj = self.create_mock_game_object("test_obj", 100.0, 200.0, (128, 64, 32, 255))

        index = icon_data.add_object(mock_obj)

        assert index == 0
        assert icon_data.count == 1
        assert icon_data.id_to_index["test_obj"] == 0
        assert icon_data.index_to_id[0] == "test_obj"

        # Check data was updated correctly
        if icon_data.data is not None:
            element = icon_data.data[0]
            np.testing.assert_array_equal(element['position'], [100.0, 200.0])
            np.testing.assert_array_almost_equal(element['color'], [128 / 255.0, 64 / 255.0, 32 / 255.0, 1.0])
            assert element['scale'] == 10.0

    def test_add_multiple_objects(self):
        """Test adding multiple game objects."""
        icon_data = IconRenderData(10)

        objects = [
            self.create_mock_game_object("obj1", 10.0, 20.0),
            self.create_mock_game_object("obj2", 30.0, 40.0),
            self.create_mock_game_object("obj3", 50.0, 60.0)
        ]

        indices = []
        for obj in objects:
            indices.append(icon_data.add_object(obj))

        assert indices == [0, 1, 2]
        assert icon_data.count == 3

        # Check all objects are properly indexed
        for i, obj in enumerate(objects):
            assert icon_data.id_to_index[obj.object_id] == i
            assert icon_data.index_to_id[i] == obj.object_id

    def test_remove_object_existing(self):
        """Test removing an existing object."""
        icon_data = IconRenderData(10)

        # Add three objects
        objects = [
            self.create_mock_game_object("obj1", 10.0, 20.0),
            self.create_mock_game_object("obj2", 30.0, 40.0),
            self.create_mock_game_object("obj3", 50.0, 60.0)
        ]

        for obj in objects:
            icon_data.add_object(obj)

        # Remove middle object
        icon_data.remove_object("obj2")

        assert icon_data.count == 2
        assert "obj2" not in icon_data.id_to_index
        # obj3 should now be at index 1 (swapped from index 2)
        assert icon_data.id_to_index["obj3"] == 1
        assert icon_data.index_to_id[1] == "obj3"
        # Check that obj3's data was moved correctly
        if icon_data.data is not None:
            np.testing.assert_array_equal(icon_data.data[1]['position'], [50.0, 60.0])

    def test_remove_object_nonexistent(self):
        """Test removing a non-existent object (should not raise error)."""
        icon_data = IconRenderData(10)
        mock_obj = self.create_mock_game_object("existing", 10.0, 20.0)
        icon_data.add_object(mock_obj)

        # This should not raise an error
        icon_data.remove_object("nonexistent")

        # Original object should still be there
        assert icon_data.count == 1
        assert "existing" in icon_data.id_to_index

    def test_update_existing_object(self):
        """Test updating an existing object."""
        icon_data = IconRenderData(10)
        mock_obj = self.create_mock_game_object("test_obj", 10.0, 20.0, (255, 0, 0, 255))
        icon_data.add_object(mock_obj)

        # Update object properties
        mock_obj.U = 100.0
        mock_obj.V = 200.0
        mock_obj.color_rgba = (0, 255, 0, 255)

        icon_data.update_object(mock_obj)

        # Should still have one object at same index
        assert icon_data.count == 1
        assert icon_data.id_to_index["test_obj"] == 0

        # Data should be updated
        if icon_data.data is not None:
            element = icon_data.data[0]
            np.testing.assert_array_equal(element['position'], [100.0, 200.0])
            np.testing.assert_array_almost_equal(element['color'], [0.0, 1.0, 0.0, 1.0])

    def test_update_nonexistent_object_adds_it(self):
        """Test that updating a non-existent object adds it."""
        icon_data = IconRenderData(10)
        mock_obj = self.create_mock_game_object("new_obj", 50.0, 75.0)

        icon_data.update_object(mock_obj)

        assert icon_data.count == 1
        assert "new_obj" in icon_data.id_to_index
        assert icon_data.index_to_id[0] == "new_obj"

    def test_color_normalization(self):
        """Test that colors are properly normalized from 0-255 to 0.0-1.0."""
        icon_data = IconRenderData(10)

        # Test with values > 1.0 (should be normalized)
        mock_obj1 = self.create_mock_game_object("obj1", 0, 0, (255, 128, 64, 200))
        icon_data.add_object(mock_obj1)

        if icon_data.data is not None:
            element1 = icon_data.data[0]
            expected_color1 = [255 / 255.0, 128 / 255.0, 64 / 255.0, 200 / 255.0]
            np.testing.assert_array_almost_equal(element1['color'], expected_color1)

        # Test with values <= 1.0 (should not be normalized)
        mock_obj2 = self.create_mock_game_object("obj2", 0, 0, (0.5, 0.8, 0.1, 1.0))
        icon_data.add_object(mock_obj2)

        if icon_data.data is not None:
            element2 = icon_data.data[1]
            expected_color2 = [0.5, 0.8, 0.1, 1.0]
            np.testing.assert_array_almost_equal(element2['color'], expected_color2)

    def test_override_color_priority(self):
        """Test that override_color takes priority over color_rgba."""
        icon_data = IconRenderData(10)
        mock_obj = self.create_mock_game_object("test_obj",
                                                0,
                                                0,
                                                color_rgba=(255, 0, 0, 255),
                                                override_color=(0, 255, 0, 255))

        icon_data.add_object(mock_obj)

        if icon_data.data is not None:
            element = icon_data.data[0]
            # Should use override_color (green), not color_rgba (red)
            np.testing.assert_array_almost_equal(element['color'], [0.0, 1.0, 0.0, 1.0])

    def test_get_render_data_empty(self):
        """Test get_render_data returns None when empty."""
        icon_data = IconRenderData(10)

        result = icon_data.get_render_data()
        assert result is None

    def test_get_render_data_with_objects(self):
        """Test get_render_data returns active portion of array."""
        icon_data = IconRenderData(10)

        # Add some objects
        for i in range(3):
            obj = self.create_mock_game_object(f"obj{i}", float(i * 10), float(i * 20))
            icon_data.add_object(obj)

        render_data = icon_data.get_render_data()

        assert render_data is not None
        assert len(render_data) == 3

        # Verify data integrity
        for i in range(3):
            np.testing.assert_array_equal(render_data[i]['position'], [i * 10.0, i * 20.0])

    def test_scale_is_constant(self):
        """Test that scale is set to a constant value (10.0)."""
        icon_data = IconRenderData(10)
        mock_obj = self.create_mock_game_object("test_obj", 0, 0)

        icon_data.add_object(mock_obj)

        if icon_data.data is not None:
            assert icon_data.data[0]['scale'] == 10.0

    def test_array_auto_resize(self):
        """Test that array automatically resizes when capacity is exceeded."""
        icon_data = IconRenderData(2)  # Small initial capacity

        # Add objects beyond initial capacity
        for i in range(5):
            obj = self.create_mock_game_object(f"obj{i}", float(i), float(i))
            icon_data.add_object(obj)

        assert icon_data.count == 5
        assert icon_data.capacity >= 5  # Should have resized

        # All objects should still be accessible
        for i in range(5):
            assert f"obj{i}" in icon_data.id_to_index
            assert icon_data.index_to_id[i] == f"obj{i}"


class TestVelocityVectorRenderData:
    """Test suite for VelocityVectorRenderData class."""

    def create_mock_game_object(self,
                                object_id: str,
                                u: float = 0.0,
                                v: float = 0.0,
                                heading: float = 0.0,
                                cas: float = 0.0,
                                color_rgba: tuple = (255, 255, 255, 255),
                                override_color: Optional[tuple] = None) -> Mock:
        """Create a mock GameObject for testing."""
        mock_obj = Mock(spec=GameObject)
        mock_obj.object_id = object_id
        mock_obj.U = u
        mock_obj.V = v
        mock_obj.Heading = heading
        mock_obj.CAS = cas
        mock_obj.color_rgba = color_rgba
        mock_obj.override_color = override_color
        return mock_obj

    def test_initialization(self):
        """Test VelocityVectorRenderData initialization."""
        velocity_data = VelocityVectorRenderData(100)

        assert velocity_data.capacity == 100
        assert velocity_data.count == 0
        assert velocity_data.data is not None
        assert len(velocity_data.data) == 100

    def test_dtype_structure(self):
        """Test that the numpy dtype has correct structure."""
        velocity_data = VelocityVectorRenderData(10)
        dtype = velocity_data._get_dtype()

        assert dtype.names == ('start_position', 'heading', 'velocity', 'color')
        assert dtype['start_position'].shape == (2, )  # x, y coordinates
        assert dtype['color'].shape == (4, )  # RGBA values
        assert dtype['heading'].shape == ()  # scalar heading
        assert dtype['velocity'].shape == ()  # scalar velocity

    def test_add_velocity_vector(self):
        """Test adding a game object to the velocity vector array."""
        velocity_data = VelocityVectorRenderData(10)
        mock_obj = self.create_mock_game_object("aircraft1", 100.0, 200.0, 45.0, 250.0, (255, 0, 0, 255))

        index = velocity_data.add_object(mock_obj)

        assert index == 0
        assert velocity_data.count == 1
        assert velocity_data.id_to_index["aircraft1"] == 0
        assert velocity_data.index_to_id[0] == "aircraft1"

        # Check data was updated correctly
        if velocity_data.data is not None:
            element = velocity_data.data[0]
            np.testing.assert_array_equal(element['start_position'], [100.0, 200.0])
            assert element['heading'] == 45.0
            assert element['velocity'] == 250.0
            np.testing.assert_array_almost_equal(element['color'], [1.0, 0.0, 0.0, 1.0])

    def test_update_velocity_vector(self):
        """Test updating an existing velocity vector."""
        velocity_data = VelocityVectorRenderData(10)
        mock_obj = self.create_mock_game_object("aircraft1", 0.0, 0.0, 0.0, 100.0)

        velocity_data.add_object(mock_obj)

        # Update the object data
        mock_obj.U = 150.0
        mock_obj.V = 250.0
        mock_obj.Heading = 90.0
        mock_obj.CAS = 300.0

        velocity_data.update_object(mock_obj)

        if velocity_data.data is not None:
            element = velocity_data.data[0]
            np.testing.assert_array_equal(element['start_position'], [150.0, 250.0])
            assert element['heading'] == 90.0
            assert element['velocity'] == 300.0

    def test_remove_velocity_vector(self):
        """Test removing a velocity vector."""
        velocity_data = VelocityVectorRenderData(10)
        mock_obj = self.create_mock_game_object("aircraft1", 100.0, 200.0, 45.0, 250.0)

        velocity_data.add_object(mock_obj)
        assert velocity_data.count == 1

        velocity_data.remove_object("aircraft1")
        assert velocity_data.count == 0
        assert "aircraft1" not in velocity_data.id_to_index

    def test_color_normalization_override(self):
        """Test that override color takes precedence and is properly normalized."""
        velocity_data = VelocityVectorRenderData(10)
        mock_obj = self.create_mock_game_object("aircraft1",
                                                0.0,
                                                0.0,
                                                0.0,
                                                100.0,
                                                color_rgba=(128, 128, 128, 255),
                                                override_color=(255, 0, 128, 128))

        velocity_data.add_object(mock_obj)

        if velocity_data.data is not None:
            element = velocity_data.data[0]
            # Should use override_color, normalized to 0.0-1.0
            np.testing.assert_array_almost_equal(element['color'], [1.0, 0.0, 128 / 255.0, 128 / 255.0])


class TestLockLineRenderData:
    """Test suite for LockLineRenderData class."""

    def create_mock_game_object(self,
                                object_id: str,
                                u: float = 0.0,
                                v: float = 0.0,
                                locked_targets: Optional[list] = None,
                                color_rgba: tuple = (255, 255, 255, 255),
                                override_color: Optional[tuple] = None) -> Mock:
        """Create a mock GameObject for testing."""
        mock_obj = Mock(spec=GameObject)
        mock_obj.object_id = object_id
        mock_obj.U = u
        mock_obj.V = v
        mock_obj.locked_target_objs = locked_targets if locked_targets is not None else []
        mock_obj.color_rgba = color_rgba
        mock_obj.override_color = override_color
        return mock_obj

    def test_initialization(self):
        """Test LockLineRenderData initialization."""
        lock_data = LockLineRenderData(100)

        assert lock_data.capacity == 100
        assert lock_data.count == 0
        assert lock_data.data is not None
        assert len(lock_data.data) == 100
        assert isinstance(lock_data.id_to_locks, dict)
        assert len(lock_data.id_to_locks) == 0

    def test_dtype_structure(self):
        """Test that the numpy dtype has correct structure."""
        lock_data = LockLineRenderData(10)
        dtype = lock_data._get_dtype()

        assert dtype.names == ('start_position', 'end_position', 'color')
        assert dtype['start_position'].shape == (2, )  # x, y coordinates
        assert dtype['end_position'].shape == (2, )  # x, y coordinates
        assert dtype['color'].shape == (4, )  # RGBA values

    def test_add_lock_line(self):
        """Test adding a lock line between two objects."""
        lock_data = LockLineRenderData(10)
        source_obj = self.create_mock_game_object("source", 0.0, 0.0, color_rgba=(255, 0, 0, 255))
        target_obj = self.create_mock_game_object("target", 100.0, 200.0)

        index = lock_data.add_lock_line(source_obj, target_obj)

        assert index == 0
        assert lock_data.count == 1
        assert "source" in lock_data.id_to_locks
        assert "target" in lock_data.id_to_locks["source"]
        assert lock_data.id_to_locks["source"]["target"] == 0
        assert lock_data.id_to_index["source:target"] == 0
        assert lock_data.index_to_id[0] == "source:target"

        # Check data was updated correctly
        if lock_data.data is not None:
            element = lock_data.data[0]
            np.testing.assert_array_equal(element['start_position'], [0.0, 0.0])
            np.testing.assert_array_equal(element['end_position'], [100.0, 200.0])
            # Color should be slightly enhanced from source (multiplied by 1.2)
            expected_color = [min(1.0, 1.0 * 1.2), min(1.0, 0.0 * 1.2), min(1.0, 0.0 * 1.2), min(1.0, 1.0 * 1.2)]
            np.testing.assert_array_almost_equal(element['color'], expected_color)

    def test_remove_lock_line(self):
        """Test removing a specific lock line."""
        lock_data = LockLineRenderData(10)
        source_obj = self.create_mock_game_object("source", 0.0, 0.0)
        target_obj = self.create_mock_game_object("target", 100.0, 200.0)

        lock_data.add_lock_line(source_obj, target_obj)
        assert lock_data.count == 1

        lock_data.remove_lock_line("source", "target")
        assert lock_data.count == 0
        assert "source" not in lock_data.id_to_locks
        assert "source:target" not in lock_data.id_to_index

    def test_update_all_locks_add_new(self):
        """Test update_all_locks adds new lock lines."""
        lock_data = LockLineRenderData(10)
        target1 = self.create_mock_game_object("target1", 50.0, 50.0)
        target2 = self.create_mock_game_object("target2", 100.0, 100.0)
        source_obj = self.create_mock_game_object("source", 0.0, 0.0, locked_targets=[target1, target2])

        lock_data.update_all_locks(source_obj)

        assert lock_data.count == 2
        assert "source" in lock_data.id_to_locks
        assert "target1" in lock_data.id_to_locks["source"]
        assert "target2" in lock_data.id_to_locks["source"]

    def test_update_all_locks_remove_old(self):
        """Test update_all_locks removes old lock lines."""
        lock_data = LockLineRenderData(10)
        target1 = self.create_mock_game_object("target1", 50.0, 50.0)
        target2 = self.create_mock_game_object("target2", 100.0, 100.0)
        source_obj = self.create_mock_game_object("source", 0.0, 0.0)

        # Add two lock lines initially
        lock_data.add_lock_line(source_obj, target1)
        lock_data.add_lock_line(source_obj, target2)
        assert lock_data.count == 2

        # Update with only one target
        source_obj.locked_target_objs = [target1]
        lock_data.update_all_locks(source_obj)

        assert lock_data.count == 1
        assert "target1" in lock_data.id_to_locks["source"]
        assert "target2" not in lock_data.id_to_locks["source"]

    def test_update_all_locks_mixed_changes(self):
        """Test update_all_locks handles mixed add/remove/update operations."""
        lock_data = LockLineRenderData(10)
        target1 = self.create_mock_game_object("target1", 50.0, 50.0)
        target2 = self.create_mock_game_object("target2", 100.0, 100.0)
        target3 = self.create_mock_game_object("target3", 150.0, 150.0)
        source_obj = self.create_mock_game_object("source", 0.0, 0.0)

        # Start with target1 and target2
        lock_data.add_lock_line(source_obj, target1)
        lock_data.add_lock_line(source_obj, target2)
        assert lock_data.count == 2

        # Update to target1 and target3 (remove target2, add target3)
        source_obj.locked_target_objs = [target1, target3]
        lock_data.update_all_locks(source_obj)

        assert lock_data.count == 2
        assert "target1" in lock_data.id_to_locks["source"]
        assert "target2" not in lock_data.id_to_locks["source"]
        assert "target3" in lock_data.id_to_locks["source"]

    def test_remove_object_locks(self):
        """Test removing all lock lines for an object (as source and target)."""
        lock_data = LockLineRenderData(10)
        obj1 = self.create_mock_game_object("obj1", 0.0, 0.0)
        obj2 = self.create_mock_game_object("obj2", 50.0, 50.0)
        obj3 = self.create_mock_game_object("obj3", 100.0, 100.0)

        # Create various lock lines involving obj2
        lock_data.add_lock_line(obj1, obj2)  # obj2 as target
        lock_data.add_lock_line(obj2, obj3)  # obj2 as source
        lock_data.add_lock_line(obj2, obj1)  # obj2 as source
        assert lock_data.count == 3

        lock_data.remove_object_locks("obj2")

        assert lock_data.count == 0
        assert "obj2" not in lock_data.id_to_locks
        assert "obj1" not in lock_data.id_to_locks

    def test_abandoned_locklines_bug_detection(self):
        """
        Test for the specific bug where lock lines could be abandoned due to 
        stale index references after swap-and-remove operations.
        
        This test reproduces a scenario where the id_to_locks mapping contains
        invalid indices after object removals, which would lead to abandoned
        lock lines remaining on screen.
        """
        lock_data = LockLineRenderData(10)

        # Create a network of objects with lock lines
        objects = {}
        for i in range(1, 6):
            objects[f'obj{i}'] = self.create_mock_game_object(f'obj{i}', i * 10.0, i * 10.0)

        # Create a specific pattern of lock lines that triggers the bug
        # obj1 -> obj2, obj3 -> obj4, obj5 -> obj1, obj2 -> obj3, obj4 -> obj5
        lock_pairs = [
            ('obj1', 'obj2'),  # index 0
            ('obj3', 'obj4'),  # index 1  
            ('obj5', 'obj1'),  # index 2
            ('obj2', 'obj3'),  # index 3
            ('obj4', 'obj5')  # index 4
        ]

        for source_id, target_id in lock_pairs:
            lock_data.add_lock_line(objects[source_id], objects[target_id])

        assert lock_data.count == 5

        # Remove obj3 which is involved in multiple lock lines
        # This should remove lock lines at indices 1 and 3
        # The bug would manifest as invalid indices in id_to_locks after removal
        lock_data.remove_object_locks('obj3')

        # Verify no stale indices remain
        for source_id, targets in lock_data.id_to_locks.items():
            for target_id, index in targets.items():
                assert index < lock_data.count, f"Invalid index {index} for {source_id}:{target_id} after removal"

        # Verify we can still add new lock lines without issues
        new_obj = self.create_mock_game_object('new_obj', 999.0, 999.0)
        initial_count = lock_data.count
        lock_data.add_lock_line(objects['obj1'], new_obj)
        assert lock_data.count == initial_count + 1

    def test_multiple_consecutive_removals(self):
        """
        Test multiple consecutive object removals to ensure the index mapping
        remains consistent throughout multiple swap operations.
        """
        lock_data = LockLineRenderData(10)

        # Create objects and a complex web of lock lines
        objects = {}
        for i in range(1, 7):
            objects[f'obj{i}'] = self.create_mock_game_object(f'obj{i}', i * 10.0, i * 10.0)

        # Create lock lines: obj1->obj2, obj2->obj3, obj3->obj4, obj4->obj5, obj5->obj6, obj6->obj1
        for i in range(1, 7):
            next_i = (i % 6) + 1
            lock_data.add_lock_line(objects[f'obj{i}'], objects[f'obj{next_i}'])

        initial_count = lock_data.count
        assert initial_count == 6

        # Remove multiple objects in sequence
        objects_to_remove = ['obj1', 'obj3', 'obj5']
        expected_removals = 0

        for obj_id in objects_to_remove:
            # Count how many lock lines involve this object
            removals_for_this_obj = 0
            if obj_id in lock_data.id_to_locks:
                removals_for_this_obj += len(lock_data.id_to_locks[obj_id])

            for source_id, targets in lock_data.id_to_locks.items():
                if obj_id in targets:
                    removals_for_this_obj += 1

            expected_removals += removals_for_this_obj
            lock_data.remove_object_locks(obj_id)

            # Verify index consistency after each removal
            for source_id, targets in lock_data.id_to_locks.items():
                for target_id, index in targets.items():
                    assert index < lock_data.count, f"Invalid index {index} for {source_id}:{target_id} after removing {obj_id}"

        # Final verification - should have removed all lock lines since each object was involved in exactly 2 lock lines
        assert lock_data.count == 0


class TestTrackRenderDataArrays:
    """Test suite for TrackRenderDataArrays master container."""

    def create_mock_game_object(
        self,
        object_id: str,
        obj_type: GameObjectType = GameObjectType.FIXEDWING,
        u: float = 0.0,
        v: float = 0.0,
        icon: Optional[int] = 1,  # Use valid shape idx=1 (CIRCLE)
        cas: float = 0.0,
        heading: float = 0.0,
        locked_targets: Optional[list] = None,
        color_rgba: tuple = (255, 255, 255, 255)) -> Mock:
        """Create a mock GameObject for testing."""
        mock_obj = Mock(spec=GameObject)
        mock_obj.object_id = object_id
        mock_obj.object_type = obj_type
        mock_obj.U = u
        mock_obj.V = v
        mock_obj.icon = icon
        mock_obj.CAS = cas
        mock_obj.Heading = heading
        mock_obj.locked_target_objs = locked_targets if locked_targets is not None else []
        mock_obj.color_rgba = color_rgba
        mock_obj.override_color = None
        mock_obj.is_air_unit = Mock(
            return_value=(obj_type == GameObjectType.FIXEDWING or obj_type == GameObjectType.ROTARYWING))
        return mock_obj

    def test_initialization(self):
        """Test TrackRenderDataArrays initialization."""
        render_arrays = TrackRenderDataArrays(100)

        # Check that all shape types have IconRenderData
        assert len(render_arrays.icon_data) == len(Shapes)
        for shape in Shapes:
            assert shape in render_arrays.icon_data
            assert isinstance(render_arrays.icon_data[shape], IconRenderData)
            assert render_arrays.icon_data[shape].capacity == 100

        # Check velocity vectors and lock lines
        assert isinstance(render_arrays.velocity_vectors, VelocityVectorRenderData)
        assert render_arrays.velocity_vectors.capacity == 50  # initial_capacity // 2
        assert isinstance(render_arrays.lock_lines, LockLineRenderData)
        assert render_arrays.lock_lines.capacity == 50  # initial_capacity // 2

    def test_add_aircraft_object(self):
        """Test adding an aircraft object (should add to icon and velocity arrays)."""
        render_arrays = TrackRenderDataArrays(100)
        aircraft_obj = self.create_mock_game_object("aircraft1",
                                                    GameObjectType.FIXEDWING,
                                                    100.0,
                                                    200.0,
                                                    icon=1,
                                                    cas=250.0,
                                                    heading=45.0)  # icon=1 (CIRCLE)

        render_arrays.add_object(aircraft_obj)

        # Should be in icon array
        shape = Shapes.from_idx(1)  # icon=1 (CIRCLE)
        assert aircraft_obj.object_id in render_arrays.icon_data[shape].id_to_index

        # Should be in velocity vectors (aircraft with CAS > 0)
        assert aircraft_obj.object_id in render_arrays.velocity_vectors.id_to_index

    def test_add_object_with_locks(self):
        """Test adding an object with target locks."""
        render_arrays = TrackRenderDataArrays(100)
        target_obj = self.create_mock_game_object("target", icon=2)  # icon=2 (SQUARE)
        source_obj = self.create_mock_game_object("source", icon=1, locked_targets=[target_obj])  # icon=1 (CIRCLE)

        render_arrays.add_object(source_obj)

        # Should create a lock line
        assert render_arrays.lock_lines.count == 1
        assert "source" in render_arrays.lock_lines.id_to_locks
        assert "target" in render_arrays.lock_lines.id_to_locks["source"]

    def test_remove_object(self):
        """Test removing an object from all arrays."""
        render_arrays = TrackRenderDataArrays(100)
        target_obj = self.create_mock_game_object("target", icon=2)  # icon=2 (SQUARE)
        aircraft_obj = self.create_mock_game_object("aircraft1",
                                                    GameObjectType.FIXEDWING,
                                                    icon=1,
                                                    cas=250.0,
                                                    locked_targets=[target_obj])  # icon=1 (CIRCLE)

        render_arrays.add_object(aircraft_obj)

        # Verify object is in arrays
        shape = Shapes.from_idx(1)  # icon=1 (CIRCLE)
        assert aircraft_obj.object_id in render_arrays.icon_data[shape].id_to_index
        assert aircraft_obj.object_id in render_arrays.velocity_vectors.id_to_index
        assert render_arrays.lock_lines.count == 1

        render_arrays.remove_object(aircraft_obj)

        # Should be removed from all arrays
        assert aircraft_obj.object_id not in render_arrays.icon_data[shape].id_to_index
        assert aircraft_obj.object_id not in render_arrays.velocity_vectors.id_to_index
        assert render_arrays.lock_lines.count == 0

    def test_update_object_velocity_change(self):
        """Test updating an aircraft object when velocity changes."""
        render_arrays = TrackRenderDataArrays(100)
        aircraft_obj = self.create_mock_game_object("aircraft1", GameObjectType.FIXEDWING, icon=1,
                                                    cas=0.0)  # Initially no velocity, icon=1 (CIRCLE)

        render_arrays.add_object(aircraft_obj)

        # Should not be in velocity vectors initially
        assert aircraft_obj.object_id not in render_arrays.velocity_vectors.id_to_index

        # Update with velocity
        aircraft_obj.CAS = 250.0
        render_arrays.update_object(aircraft_obj)

        # Should now be in velocity vectors
        assert aircraft_obj.object_id in render_arrays.velocity_vectors.id_to_index

    def test_update_object_lock_changes(self):
        """Test updating an object when lock targets change."""
        render_arrays = TrackRenderDataArrays(100)
        target1 = self.create_mock_game_object("target1", icon=2)  # icon=2 (SQUARE)
        target2 = self.create_mock_game_object("target2", icon=2)  # icon=2 (SQUARE)
        source_obj = self.create_mock_game_object("source", icon=1, locked_targets=[target1])  # icon=1 (CIRCLE)

        render_arrays.add_object(source_obj)
        assert render_arrays.lock_lines.count == 1

        # Change locked targets
        source_obj.locked_target_objs = [target1, target2]
        render_arrays.update_object(source_obj)

        # Should now have 2 lock lines
        assert render_arrays.lock_lines.count == 2
        assert "target1" in render_arrays.lock_lines.id_to_locks["source"]
        assert "target2" in render_arrays.lock_lines.id_to_locks["source"]

    def test_get_render_data(self):
        """Test getting render data for GPU rendering."""
        render_arrays = TrackRenderDataArrays(100)
        aircraft_obj = self.create_mock_game_object("aircraft1", GameObjectType.FIXEDWING, icon=1,
                                                    cas=250.0)  # icon=1 (CIRCLE)

        render_arrays.add_object(aircraft_obj)

        render_data = render_arrays.get_render_data()

        assert render_data is not None
        assert 'icons' in render_data
        assert 'velocity_vectors' in render_data
        assert 'lock_lines' in render_data

        # Check that icon data is present
        assert isinstance(render_data['icons'], dict)
        shape = Shapes.from_idx(1)  # icon=1 (CIRCLE)
        assert shape in render_data['icons']
        assert render_data['icons'][shape] is not None

        # Check velocity vectors
        assert render_data['velocity_vectors'] is not None
        assert len(render_data['velocity_vectors']) == 1


def test_mock_render_data_integration():
    """Integration test to verify MockRenderData works as expected."""
    mock_data = MockRenderData(10)

    # Add some test data manually
    mock_data.count = 2
    mock_data.id_to_index["test1"] = 0
    mock_data.index_to_id[0] = "test1"
    mock_data.id_to_index["test2"] = 1
    mock_data.index_to_id[1] = "test2"

    if mock_data.data is not None:
        mock_data.data[0]['test_field'] = 1.5
        mock_data.data[0]['another_field'] = 10
        mock_data.data[1]['test_field'] = 2.5
        mock_data.data[1]['another_field'] = 20

    # Test remove by swap
    mock_data._remove_by_swap(0, "test1")

    assert mock_data.count == 1
    assert "test1" not in mock_data.id_to_index
    assert mock_data.id_to_index["test2"] == 0  # Should have been swapped
    if mock_data.data is not None:
        assert mock_data.data[0]['test_field'] == 2.5
        assert mock_data.data[0]['another_field'] == 20


class TestLineRenderData:
    """Test suite for flexible LineRenderData class."""

    def test_initialization_default(self):
        """Test LineRenderData initialization with default parameters."""
        line_data = LineRenderData()
        
        assert line_data.line_capacity == 1000
        assert line_data.points_capacity == 10000
        assert line_data.get_line_count() == 0
        assert line_data.get_points_count() == 0
        assert isinstance(line_data.id_to_index, dict)
        assert isinstance(line_data.line_metadata, np.ndarray)
        assert isinstance(line_data.points_array, np.ndarray)
        assert len(line_data.id_to_index) == 0

    def test_initialization_custom_capacity(self):
        """Test LineRenderData initialization with custom capacities."""
        line_data = LineRenderData(initial_capacity=100, initial_points_capacity=1000)
        
        assert line_data.line_capacity == 100
        assert line_data.points_capacity == 1000
        assert line_data.get_line_count() == 0
        assert line_data.get_points_count() == 0

    def test_add_line_simple(self):
        """Test adding a simple 2-point line."""
        line_data = LineRenderData()
        points = [(0.0, 0.0), (100.0, 100.0)]
        
        line_data.add_line("line1", points, width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        
        assert line_data.get_line_count() == 1
        assert line_data.get_points_count() == 2
        assert "line1" in line_data.id_to_index
        assert line_data.id_to_index["line1"] == 0

    def test_add_line_complex(self):
        """Test adding a complex multi-point line."""
        line_data = LineRenderData()
        points_list = [(0, 0), (50, 50), (100, 0), (150, 100), (200, 50)]
        
        line_data.add_line("complex_line", points_list, width=2.5, color=(0.0, 1.0, 0.0, 1.0))
        
        assert line_data.get_line_count() == 1
        assert line_data.get_points_count() == 5
        
        # Check that points were stored correctly
        metadata, points = line_data.get_render_data()
        assert points is not None
        for i, (x, y) in enumerate(points_list):
            assert points[i]['position'][0] == float(x)
            assert points[i]['position'][1] == float(y)

    def test_add_multiple_lines(self):
        """Test adding multiple lines with different point counts."""
        line_data = LineRenderData()
        
        # Add first line (2 points)
        line_data.add_line("line1", [(0, 0), (10, 10)], width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        
        # Add second line (3 points)
        line_data.add_line("line2", [(20, 20), (30, 30), (40, 40)], width=2.0, color=(0.0, 1.0, 0.0, 1.0))
        
        # Add third line (4 points)
        line_data.add_line("line3", [(50, 50), (60, 60), (70, 70), (80, 80)], 
                          width=3.0, color=(0.0, 0.0, 1.0, 1.0))
        
        assert line_data.get_line_count() == 3
        assert line_data.get_points_count() == 9  # 2 + 3 + 4 = 9
        
        # Check all IDs are mapped
        assert "line1" in line_data.id_to_index
        assert "line2" in line_data.id_to_index
        assert "line3" in line_data.id_to_index
        
        # Check indices are sequential
        assert line_data.id_to_index["line1"] == 0
        assert line_data.id_to_index["line2"] == 1
        assert line_data.id_to_index["line3"] == 2

    def test_add_line_duplicate_id_raises_error(self):
        """Test that adding a line with duplicate ID raises ValueError."""
        line_data = LineRenderData()
        
        line_data.add_line("duplicate", [(0, 0), (10, 10)], width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        
        with pytest.raises(ValueError, match="Line with ID 'duplicate' already exists"):
            line_data.add_line("duplicate", [(20, 20), (30, 30)], width=2.0, color=(0.0, 1.0, 0.0, 1.0))

    def test_add_line_empty_points_raises_error(self):
        """Test that adding a line with no points raises ValueError."""
        line_data = LineRenderData()
        
        with pytest.raises(ValueError, match="Points list cannot be empty"):
            line_data.add_line("empty", [], width=1.0, color=(1.0, 0.0, 0.0, 1.0))

    def test_update_line_existing(self):
        """Test updating an existing line with new points."""
        line_data = LineRenderData()
        
        # Add initial line
        line_data.add_line("updatable", [(0, 0), (10, 10)], width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        assert line_data.get_points_count() == 2
        
        # Update with more points
        new_points = [(5, 5), (15, 15), (25, 25), (35, 35)]
        line_data.update_line("updatable", new_points, width=2.5, color=(0.0, 0.0, 1.0, 1.0))
        
        assert line_data.get_line_count() == 1  # Still one line
        # Points count might be higher due to points array management
        assert line_data.get_points_count() >= 4  # At least the new points
        
        # Verify the line metadata was updated
        metadata, points = line_data.get_render_data()
        assert metadata is not None
        assert metadata[0]['width'] == 2.5
        assert np.array_equal(metadata[0]['color'], [0.0, 0.0, 1.0, 1.0])

    def test_update_line_partial_parameters(self):
        """Test updating a line with only some parameters changed."""
        line_data = LineRenderData()
        
        # Add initial line
        original_color = (1.0, 0.0, 0.0, 1.0)
        line_data.add_line("partial", [(0, 0), (10, 10)], width=1.0, color=original_color)
        
        # Update only width, keeping original color
        new_points = [(0, 0), (20, 20)]
        line_data.update_line("partial", new_points, width=3.0)
        
        metadata, points = line_data.get_render_data()
        assert metadata is not None
        assert metadata[0]['width'] == 3.0
        assert np.array_equal(metadata[0]['color'], original_color)  # Should remain unchanged

    def test_update_line_nonexistent_raises_error(self):
        """Test that updating a non-existent line raises ValueError."""
        line_data = LineRenderData()
        
        with pytest.raises(ValueError, match="Line with ID 'nonexistent' not found"):
            line_data.update_line("nonexistent", [(0, 0), (10, 10)], width=1.0)

    def test_remove_line_existing(self):
        """Test removing an existing line."""
        line_data = LineRenderData()
        
        # Add multiple lines
        line_data.add_line("line1", [(0, 0), (10, 10)], width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        line_data.add_line("line2", [(20, 20), (30, 30), (40, 40)], width=2.0, color=(0.0, 1.0, 0.0, 1.0))
        line_data.add_line("line3", [(50, 50), (60, 60)], width=3.0, color=(0.0, 0.0, 1.0, 1.0))
        
        assert line_data.get_line_count() == 3
        assert line_data.get_points_count() == 7  # 2 + 3 + 2 = 7
        
        # Remove middle line
        line_data.remove_line("line2")
        
        assert line_data.get_line_count() == 2
        # Points are not cleaned up, so count remains the same
        assert line_data.get_points_count() == 7  # Points array not compacted
        assert "line2" not in line_data.id_to_index
        assert "line1" in line_data.id_to_index
        assert "line3" in line_data.id_to_index

    def test_remove_line_nonexistent_raises_error(self):
        """Test that removing a non-existent line raises ValueError."""
        line_data = LineRenderData()
        
        with pytest.raises(ValueError, match="Line with ID 'nonexistent' not found"):
            line_data.remove_line("nonexistent")

    def test_get_render_data_empty(self):
        """Test getting render data when no lines exist."""
        line_data = LineRenderData()
        
        metadata, points = line_data.get_render_data()
        
        assert metadata is None
        assert points is None

    def test_get_render_data_with_lines(self):
        """Test getting render data with multiple lines."""
        line_data = LineRenderData()
        
        # Add lines with different characteristics
        line_data.add_line("red_line", [(0, 0), (10, 10)], width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        line_data.add_line("green_triangle", [(20, 20), (30, 30), (40, 20), (20, 20)], 
                          width=2.0, color=(0.0, 1.0, 0.0, 1.0))
        line_data.add_line("blue_path", [(50, 50), (60, 40), (70, 50)], 
                          width=1.5, color=(0.0, 0.0, 1.0, 1.0))
        
        metadata, points = line_data.get_render_data()
        
        assert metadata is not None
        assert points is not None
        assert len(metadata) == 3  # Three lines
        assert len(points) == 9   # 2 + 4 + 3 = 9 points total
        
        # Check metadata structure
        assert metadata.dtype.names == ('start_index', 'end_index', 'width', 'color')
        
        # Check first line metadata
        assert metadata[0]['start_index'] == 0
        assert metadata[0]['end_index'] == 2
        assert metadata[0]['width'] == 1.0
        assert np.array_equal(metadata[0]['color'], [1.0, 0.0, 0.0, 1.0])
        
        # Check second line metadata
        assert metadata[1]['start_index'] == 2
        assert metadata[1]['end_index'] == 6
        assert metadata[1]['width'] == 2.0
        assert np.array_equal(metadata[1]['color'], [0.0, 1.0, 0.0, 1.0])
        
        # Check third line metadata
        assert metadata[2]['start_index'] == 6
        assert metadata[2]['end_index'] == 9
        assert metadata[2]['width'] == 1.5
        assert np.array_equal(metadata[2]['color'], [0.0, 0.0, 1.0, 1.0])
        
        # Check points structure
        assert points.dtype.names == ('position',)
        
        # Check some point values
        assert np.array_equal(points[0]['position'], [0.0, 0.0])
        assert np.array_equal(points[1]['position'], [10.0, 10.0])
        assert np.array_equal(points[2]['position'], [20.0, 20.0])  # Start of second line

    def test_points_array_not_defragmented(self):
        """Test that points array is not defragmented after removing lines."""
        line_data = LineRenderData()
        
        # Add three lines
        line_data.add_line("line1", [(0, 0), (10, 10)], width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        line_data.add_line("line2", [(20, 20), (30, 30), (40, 40)], width=2.0, color=(0.0, 1.0, 0.0, 1.0))
        line_data.add_line("line3", [(50, 50), (60, 60)], width=3.0, color=(0.0, 0.0, 1.0, 1.0))
        
        # Remove middle line (creates fragmentation)
        line_data.remove_line("line2")
        
        # Points array is not defragmented, so all points remain
        metadata, points = line_data.get_render_data()
        
        assert metadata is not None
        assert points is not None
        assert len(metadata) == 2  # Only 2 lines remaining
        assert len(points) == 7   # But all 7 points still in array (not compacted)
        
        # The remaining lines' metadata should still be valid
        # Even though the points array contains fragmented data

    def test_clear_all_lines(self):
        """Test clearing all lines."""
        line_data = LineRenderData()
        
        # Add some lines
        line_data.add_line("line1", [(0, 0), (10, 10)], width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        line_data.add_line("line2", [(20, 20), (30, 30)], width=2.0, color=(0.0, 1.0, 0.0, 1.0))
        
        assert line_data.get_line_count() == 2
        assert line_data.get_points_count() == 4
        
        # Clear all
        line_data.clear()
        
        assert line_data.get_line_count() == 0
        assert line_data.get_points_count() == 0
        assert len(line_data.id_to_index) == 0

    def test_color_format_conversion(self):
        """Test automatic color format conversion (0-255 to 0-1 range)."""
        line_data = LineRenderData()
        
        # Add line with 0-255 color format
        line_data.add_line("colored", [(0, 0), (10, 10)], width=1.0, color=(255, 128, 64, 255))
        
        metadata, points = line_data.get_render_data()
        assert metadata is not None
        
        # Should be converted to 0-1 range
        expected_color = [255/255, 128/255, 64/255, 255/255]
        assert np.allclose(metadata[0]['color'], expected_color)

    def test_edge_case_single_point_line(self):
        """Test handling of single-point 'line' (should still work but be degenerate)."""
        line_data = LineRenderData()
        
        # Add single point (degenerate line)
        line_data.add_line("point", [(50, 50)], width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        
        assert line_data.get_line_count() == 1
        assert line_data.get_points_count() == 1
        
        metadata, points = line_data.get_render_data()
        assert metadata is not None
        assert points is not None
        assert len(points) == 1
        assert np.array_equal(points[0]['position'], [50.0, 50.0])

    def test_performance_large_number_of_lines(self):
        """Test performance and correctness with a large number of lines."""
        line_data = LineRenderData(initial_capacity=1000, initial_points_capacity=10000)
        
        # Add many lines
        num_lines = 100
        points_per_line = 10
        
        for i in range(num_lines):
            points = [(j*10 + i, j*5 + i*2) for j in range(points_per_line)]
            line_data.add_line(f"line_{i}", points, width=float(i % 5 + 1), 
                             color=(i/num_lines, 0.5, 1.0 - i/num_lines, 1.0))
        
        assert line_data.get_line_count() == num_lines
        assert line_data.get_points_count() == num_lines * points_per_line
        
        # Test getting render data
        metadata, points = line_data.get_render_data()
        assert metadata is not None
        assert points is not None
        assert len(metadata) == num_lines
        assert len(points) == num_lines * points_per_line
        
        # Test removing some lines
        for i in range(0, num_lines, 10):  # Remove every 10th line
            line_data.remove_line(f"line_{i}")
        
        expected_remaining = num_lines - len(range(0, num_lines, 10))
        assert line_data.get_line_count() == expected_remaining

    def test_memory_efficiency_vs_fixed_array(self):
        """Test that flexible array is more memory efficient than fixed arrays for varied line lengths."""
        line_data = LineRenderData()
        
        # Add lines with very different point counts to demonstrate efficiency
        line_data.add_line("short", [(0, 0), (10, 10)], width=1.0, color=(1.0, 0.0, 0.0, 1.0))  # 2 points
        line_data.add_line("medium", [(20, 20), (30, 30), (40, 40), (50, 50)], 
                          width=2.0, color=(0.0, 1.0, 0.0, 1.0))  # 4 points
        line_data.add_line("long", [(i*5, i*3) for i in range(20)], 
                          width=3.0, color=(0.0, 0.0, 1.0, 1.0))  # 20 points
        
        total_points = 2 + 4 + 20  # 26 points
        assert line_data.get_points_count() == total_points
        
        # Get render data and verify structure
        metadata, points = line_data.get_render_data()
        assert metadata is not None
        assert points is not None
        assert len(points) == total_points
        
        # Verify no padding - each line uses exactly the points it needs
        assert metadata[0]['end_index'] - metadata[0]['start_index'] == 2
        assert metadata[1]['end_index'] - metadata[1]['start_index'] == 4
        assert metadata[2]['end_index'] - metadata[2]['start_index'] == 20


class TestPolygonRenderData:
    """Test suite for PolygonRenderData class."""

    def test_initialization_default(self):
        """Test PolygonRenderData initialization with default capacity."""
        polygon_data = PolygonRenderData(100)
        
        assert polygon_data.capacity == 100
        assert polygon_data.count == 0
        assert isinstance(polygon_data.id_to_index, dict)
        assert isinstance(polygon_data.index_to_id, dict)
        assert len(polygon_data.id_to_index) == 0
        assert polygon_data.data is not None
        assert len(polygon_data.data) == 100

    def test_dtype_structure(self):
        """Test that PolygonRenderData has the correct numpy dtype structure."""
        polygon_data = PolygonRenderData(10)
        
        expected_fields = ['offset', 'scale', 'width', 'color']
        actual_fields = list(polygon_data.data.dtype.names) if polygon_data.data is not None and polygon_data.data.dtype.names is not None else []
        
        assert actual_fields == expected_fields
        
        if polygon_data.data is not None:
            # Test field types and shapes
            assert polygon_data.data.dtype['offset'].shape == (2,)  # vec2
            assert polygon_data.data.dtype['scale'].shape == ()     # float
            assert polygon_data.data.dtype['width'].shape == ()     # float
            assert polygon_data.data.dtype['color'].shape == (4,)   # vec4

    def test_add_element_with_xy_coordinates(self):
        """Test adding a polygon element using x, y coordinates."""
        polygon_data = PolygonRenderData(10)
        
        polygon_data.add_element("poly1", x=100.0, y=200.0, scale=1.5, width=2.0, color=(255, 0, 0, 255))
        
        assert polygon_data.count == 1
        assert "poly1" in polygon_data.id_to_index
        assert polygon_data.id_to_index["poly1"] == 0
        
        if polygon_data.data is not None:
            element = polygon_data.data[0]
            assert np.array_equal(element['offset'], [100.0, 200.0])
            assert element['scale'] == 1.5
            assert element['width'] == 2.0
            # Color should be normalized from 255 to 1.0 range
            assert np.allclose(element['color'], [1.0, 0.0, 0.0, 1.0])

    def test_add_element_with_offset_tuple(self):
        """Test adding a polygon element using offset tuple."""
        polygon_data = PolygonRenderData(10)
        
        polygon_data.add_element("poly2", offset=(50.0, 75.0), scale=1.0, width=1.0, color=(0.0, 1.0, 0.0, 1.0))
        
        assert polygon_data.count == 1
        
        if polygon_data.data is not None:
            element = polygon_data.data[0]
            assert np.array_equal(element['offset'], [50.0, 75.0])
            assert element['scale'] == 1.0
            assert element['width'] == 1.0
            assert np.array_equal(element['color'], [0.0, 1.0, 0.0, 1.0])

    def test_add_multiple_elements(self):
        """Test adding multiple polygon elements."""
        polygon_data = PolygonRenderData(10)
        
        # Add three different polygons
        polygon_data.add_element("poly1", x=0.0, y=0.0, scale=1.0, width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        polygon_data.add_element("poly2", offset=(50.0, 50.0), scale=2.0, width=2.0, color=(0.0, 1.0, 0.0, 1.0))
        polygon_data.add_element("poly3", x=100.0, y=100.0, scale=0.5, width=3.0, color=(0.0, 0.0, 1.0, 1.0))
        
        assert polygon_data.count == 3
        assert len(polygon_data.id_to_index) == 3
        
        # Check all IDs are mapped correctly
        assert polygon_data.id_to_index["poly1"] == 0
        assert polygon_data.id_to_index["poly2"] == 1
        assert polygon_data.id_to_index["poly3"] == 2

    def test_update_element_existing(self):
        """Test updating an existing polygon element."""
        polygon_data = PolygonRenderData(10)
        
        # Add initial element
        polygon_data.add_element("updatable", x=0.0, y=0.0, scale=1.0, width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        
        # Update the element
        polygon_data.update_element("updatable", x=50.0, y=50.0, scale=2.0, width=3.0, color=(0.0, 1.0, 0.0, 1.0))
        
        assert polygon_data.count == 1  # Still one element
        
        if polygon_data.data is not None:
            element = polygon_data.data[0]
            assert np.array_equal(element['offset'], [50.0, 50.0])
            assert element['scale'] == 2.0
            assert element['width'] == 3.0
            assert np.array_equal(element['color'], [0.0, 1.0, 0.0, 1.0])

    def test_update_element_partial_parameters(self):
        """Test updating only some parameters of an element."""
        polygon_data = PolygonRenderData(10)
        
        # Add initial element
        original_color = (1.0, 0.0, 0.0, 1.0)
        polygon_data.add_element("partial", x=0.0, y=0.0, scale=1.0, width=1.0, color=original_color)
        
        # Update only scale and width, keeping position and color
        polygon_data.update_element("partial", scale=3.0, width=5.0)
        
        if polygon_data.data is not None:
            element = polygon_data.data[0]
            assert np.array_equal(element['offset'], [0.0, 0.0])  # Should remain unchanged
            assert element['scale'] == 3.0  # Should be updated
            assert element['width'] == 5.0  # Should be updated
            assert np.array_equal(element['color'], original_color)  # Should remain unchanged

    def test_color_normalization_255_range(self):
        """Test automatic color normalization from 0-255 to 0.0-1.0 range."""
        polygon_data = PolygonRenderData(10)
        
        polygon_data.add_element("colored", x=0.0, y=0.0, scale=1.0, width=1.0, color=(255, 128, 64, 255))
        
        if polygon_data.data is not None:
            element = polygon_data.data[0]
            expected_color = [255/255, 128/255, 64/255, 255/255]
            assert np.allclose(element['color'], expected_color)

    def test_color_already_normalized(self):
        """Test that already normalized colors (0.0-1.0) are preserved."""
        polygon_data = PolygonRenderData(10)
        
        normalized_color = (0.5, 0.75, 0.25, 0.8)
        polygon_data.add_element("normalized", x=0.0, y=0.0, scale=1.0, width=1.0, color=normalized_color)
        
        if polygon_data.data is not None:
            element = polygon_data.data[0]
            assert np.allclose(element['color'], normalized_color)

    def test_remove_element_existing(self):
        """Test removing an existing polygon element."""
        polygon_data = PolygonRenderData(10)
        
        # Add multiple elements
        polygon_data.add_element("poly1", x=0.0, y=0.0, scale=1.0, width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        polygon_data.add_element("poly2", x=50.0, y=50.0, scale=2.0, width=2.0, color=(0.0, 1.0, 0.0, 1.0))
        polygon_data.add_element("poly3", x=100.0, y=100.0, scale=3.0, width=3.0, color=(0.0, 0.0, 1.0, 1.0))
        
        assert polygon_data.count == 3
        
        # Remove middle element
        polygon_data.remove_element("poly2")
        
        assert polygon_data.count == 2
        assert "poly2" not in polygon_data.id_to_index
        assert "poly1" in polygon_data.id_to_index
        assert "poly3" in polygon_data.id_to_index
        
        # poly3 should have been swapped to index 1 (where poly2 was)
        assert polygon_data.id_to_index["poly3"] == 1

    def test_remove_element_nonexistent_safe(self):
        """Test that removing a non-existent element is safe."""
        polygon_data = PolygonRenderData(10)
        
        # Should not raise an error
        polygon_data.remove_element("nonexistent")
        assert polygon_data.count == 0

    def test_get_active_data_empty(self):
        """Test getting active data when no elements exist."""
        polygon_data = PolygonRenderData(10)
        
        active_data = polygon_data.get_active_data()
        
        # Should return None when no elements exist
        assert active_data is None

    def test_get_active_data_with_elements(self):
        """Test getting active data with polygon elements."""
        polygon_data = PolygonRenderData(10)
        
        # Add some elements
        polygon_data.add_element("poly1", x=10.0, y=20.0, scale=1.5, width=2.0, color=(1.0, 0.0, 0.0, 1.0))
        polygon_data.add_element("poly2", offset=(30.0, 40.0), scale=2.5, width=3.0, color=(0.0, 1.0, 0.0, 1.0))
        
        active_data = polygon_data.get_active_data()
        
        assert active_data is not None
        assert len(active_data) == 2
        
        # Verify data structure
        assert active_data.dtype.names == ('offset', 'scale', 'width', 'color')
        
        # Check first element
        assert np.array_equal(active_data[0]['offset'], [10.0, 20.0])
        assert active_data[0]['scale'] == 1.5
        assert active_data[0]['width'] == 2.0
        assert np.array_equal(active_data[0]['color'], [1.0, 0.0, 0.0, 1.0])
        
        # Check second element
        assert np.array_equal(active_data[1]['offset'], [30.0, 40.0])
        assert active_data[1]['scale'] == 2.5
        assert active_data[1]['width'] == 3.0
        assert np.array_equal(active_data[1]['color'], [0.0, 1.0, 0.0, 1.0])

    def test_array_auto_resize(self):
        """Test that the array automatically resizes when capacity is exceeded."""
        polygon_data = PolygonRenderData(2)  # Small initial capacity
        
        # Add elements beyond initial capacity
        polygon_data.add_element("poly1", x=0.0, y=0.0, scale=1.0, width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        polygon_data.add_element("poly2", x=10.0, y=10.0, scale=2.0, width=2.0, color=(0.0, 1.0, 0.0, 1.0))
        polygon_data.add_element("poly3", x=20.0, y=20.0, scale=3.0, width=3.0, color=(0.0, 0.0, 1.0, 1.0))  # Should trigger resize
        
        assert polygon_data.count == 3
        assert polygon_data.capacity == 4  # Should have doubled from 2 to 4
        
        # Verify all elements are still accessible
        active_data = polygon_data.get_active_data()
        assert active_data is not None
        assert len(active_data) == 3

    def test_swap_with_last_removal_behavior(self):
        """Test the swap-with-last removal behavior in detail."""
        polygon_data = PolygonRenderData(10)
        
        # Add elements in specific order
        polygon_data.add_element("first", x=1.0, y=1.0, scale=1.0, width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        polygon_data.add_element("middle", x=2.0, y=2.0, scale=2.0, width=2.0, color=(0.0, 1.0, 0.0, 1.0))
        polygon_data.add_element("last", x=3.0, y=3.0, scale=3.0, width=3.0, color=(0.0, 0.0, 1.0, 1.0))
        
        # Verify initial indices
        assert polygon_data.id_to_index["first"] == 0
        assert polygon_data.id_to_index["middle"] == 1
        assert polygon_data.id_to_index["last"] == 2
        
        # Remove middle element
        polygon_data.remove_element("middle")
        
        # Last element should now be at index 1 (swapped with middle)
        assert polygon_data.id_to_index["first"] == 0  # Unchanged
        assert polygon_data.id_to_index["last"] == 1   # Moved from index 2 to 1
        assert "middle" not in polygon_data.id_to_index
        
        # Verify data integrity
        if polygon_data.data is not None:
            # First element unchanged
            assert np.array_equal(polygon_data.data[0]['offset'], [1.0, 1.0])
            assert polygon_data.data[0]['scale'] == 1.0
            
            # Last element moved to index 1
            assert np.array_equal(polygon_data.data[1]['offset'], [3.0, 3.0])
            assert polygon_data.data[1]['scale'] == 3.0

    def test_gpu_data_compatibility(self):
        """Test that generated data is compatible with GPU rendering expectations."""
        polygon_data = PolygonRenderData(10)
        
        # Add a polygon with typical rendering parameters
        polygon_data.add_element("gpu_test", x=100.0, y=200.0, scale=1.5, width=2.0, color=(128, 64, 192, 255))
        
        active_data = polygon_data.get_active_data()
        
        assert active_data is not None
        assert len(active_data) == 1
        
        # Verify data types match GPU expectations
        # For arrays with shape, we check the base type
        if active_data.dtype['offset'].subdtype is not None:
            assert active_data.dtype['offset'].subdtype[0] == np.float32  # vec2 of float32
        else:
            assert active_data.dtype['offset'].type == np.float32
            
        assert active_data.dtype['scale'] == np.float32              # float32  
        assert active_data.dtype['width'] == np.float32              # float32
        
        if active_data.dtype['color'].subdtype is not None:
            assert active_data.dtype['color'].subdtype[0] == np.float32  # vec4 of float32
        else:
            assert active_data.dtype['color'].type == np.float32
        
        # Verify color normalization for GPU (0.0-1.0 range)
        color = active_data[0]['color']
        assert all(0.0 <= c <= 1.0 for c in color)
        assert np.allclose(color, [128/255, 64/255, 192/255, 1.0])

    def test_element_id_collision_handling(self):
        """Test behavior when adding element with existing ID."""
        polygon_data = PolygonRenderData(10)
        
        # Add initial element
        polygon_data.add_element("collision", x=0.0, y=0.0, scale=1.0, width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        assert polygon_data.count == 1
        
        # Add element with same ID - GenericStructuredArray always adds new elements
        # This will create a second element with same ID (one overwrites mapping)
        polygon_data.add_element("collision", x=50.0, y=50.0, scale=2.0, width=3.0, color=(0.0, 1.0, 0.0, 1.0))
        
        # Should have 2 elements, but mapping points to the latest one
        assert polygon_data.count == 2
        assert "collision" in polygon_data.id_to_index
        
        # The mapping should point to the second element (index 1)
        assert polygon_data.id_to_index["collision"] == 1

    def test_update_element_collision_handling(self):
        """Test update_element behavior which properly handles existing IDs."""
        polygon_data = PolygonRenderData(10)
        
        # Add initial element
        polygon_data.add_element("updatable", x=0.0, y=0.0, scale=1.0, width=1.0, color=(1.0, 0.0, 0.0, 1.0))
        assert polygon_data.count == 1
        
        # Update element with same ID - should update existing
        polygon_data.update_element("updatable", x=50.0, y=50.0, scale=2.0, width=3.0, color=(0.0, 1.0, 0.0, 1.0))
        
        # Should still have only 1 element, but with updated values
        assert polygon_data.count == 1
        
        if polygon_data.data is not None:
            element = polygon_data.data[0]
            assert np.array_equal(element['offset'], [50.0, 50.0])
            assert element['scale'] == 2.0
            assert element['width'] == 3.0
            assert np.array_equal(element['color'], [0.0, 1.0, 0.0, 1.0])


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
