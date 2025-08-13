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

sys.path.append("src")
from render_data_arrays import BaseRenderData, IconRenderData, VelocityVectorRenderData, LockLineRenderData, RenderDataArrays
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


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
