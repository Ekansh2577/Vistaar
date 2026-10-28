import numpy as np

from vector_store import add_to_index, indices, search, stored_chunks_by_user


def test_search_results_are_scoped_to_the_user():
    indices.clear()
    stored_chunks_by_user.clear()
    add_to_index(np.zeros((1, 384)), ["private passage for user A"], user_id="user-a")
    add_to_index(np.zeros((1, 384)), ["private passage for user B"], user_id="user-b")

    assert search(np.zeros(384), user_id="user-a") == ["private passage for user A"]
    assert search(np.zeros(384), user_id="user-b") == ["private passage for user B"]
    assert search(np.zeros(384), user_id="user-c") == []
