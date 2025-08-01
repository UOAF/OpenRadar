import ctypes
import OpenGL.GL as gl
from OpenGL.GL.ARB import timer_query


class GPUTimer:
    """
    Manages GPU timing queries using OpenGL timer queries.
    Uses multiple query pairs with delayed checking to avoid blocking the GPU pipeline.
    """

    def __init__(self, max_query_pairs=3):
        self.query_pairs = []
        self.max_query_pairs = max_query_pairs
        self.current_query_index = 0
        self.frame_counter = 0
        self.last_gpu_time_us = 0.0

        self._create_query_pairs()

    def _create_query_pairs(self):
        for _ in range(self.max_query_pairs):
            queries = gl.glGenQueries(2)
            self.query_pairs.append((queries[0], queries[1]))

    def start_frame_timing(self):
        start_query, _ = self.query_pairs[self.current_query_index]
        gl.glQueryCounter(start_query, timer_query.GL_TIMESTAMP)

    def end_query_only(self):
        """End the GPU timing query but don't check results yet."""
        _, end_query = self.query_pairs[self.current_query_index]
        gl.glQueryCounter(end_query, timer_query.GL_TIMESTAMP)

    def check_results_and_advance(self):
        """Check delayed results and advance to next query pair."""
        self._check_delayed_results()
        self._advance_to_next_query()

    def end_frame_timing(self):
        """Original method that does both end query and result checking."""
        self.end_query_only()
        self.check_results_and_advance()

    def _advance_to_next_query(self):
        self.current_query_index = (self.current_query_index + 1) % self.max_query_pairs
        self.frame_counter += 1

    def _check_delayed_results(self):
        insufficient_frames_in_flight = self.frame_counter < 2
        if insufficient_frames_in_flight:
            return

        check_query_index = (self.current_query_index - 2) % self.max_query_pairs
        check_start_query, check_end_query = self.query_pairs[check_query_index]

        query_results_available = self._are_query_results_available(check_start_query, check_end_query)
        if not query_results_available:
            return

        self._read_timing_results(check_start_query, check_end_query)

    def _are_query_results_available(self, start_query, end_query):
        start_available = ctypes.c_uint()
        end_available = ctypes.c_uint()
        gl.glGetQueryObjectuiv(start_query, gl.GL_QUERY_RESULT_AVAILABLE, ctypes.byref(start_available))
        gl.glGetQueryObjectuiv(end_query, gl.GL_QUERY_RESULT_AVAILABLE, ctypes.byref(end_available))

        return start_available.value and end_available.value

    def _read_timing_results(self, start_query, end_query):
        start_time_ns = ctypes.c_ulonglong()
        end_time_ns = ctypes.c_ulonglong()
        gl.glGetQueryObjectui64v(start_query, gl.GL_QUERY_RESULT, ctypes.byref(start_time_ns))
        gl.glGetQueryObjectui64v(end_query, gl.GL_QUERY_RESULT, ctypes.byref(end_time_ns))

        gpu_frame_time_ns = end_time_ns.value - start_time_ns.value
        self.last_gpu_time_us = gpu_frame_time_ns / 1000.0

    def get_last_gpu_time_us(self):
        return self.last_gpu_time_us

    def cleanup(self):
        for start_query, end_query in self.query_pairs:
            gl.glDeleteQueries(2, [start_query, end_query])
        self.query_pairs.clear()
