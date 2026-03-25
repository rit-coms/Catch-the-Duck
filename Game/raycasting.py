def cast_rays(ai_pos, SCREEN_WIDTH, SCREEN_HEIGHT):
    # Calculate a distant end point for the theoretical line (raycasting)
    # This point should be far enough to cover the whole screen or more
    # A simple way for a line of sight is to use a large vector towards the mouse
    direction_vector = (ai_pos[0] - ai_pos[0], 0 - ai_pos[1])
    # Normalize and multiply by a large distance (e.g., screen dimensions)
    distance = max(SCREEN_WIDTH, SCREEN_HEIGHT)
    if direction_vector[0] != 0 or direction_vector[1] != 0:
        length = (direction_vector[0] ** 2 + direction_vector[1] ** 2) ** 0.5
        normalized_direction = (direction_vector[0] / length, direction_vector[1] / length)
        far_end_pos = (ai_pos[0] + normalized_direction[0] * distance,
                       ai_pos[1] + normalized_direction[1] * distance)

    return far_end_pos
