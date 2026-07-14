import dearpygui.dearpygui as dpg


# Control points interactive logic
class ControlPointsInput:
    def __init__(self):
        self.control_points = [
            {"id": "inlet",  "label": "Coolant Inlet",  "fixed": True, "position": 0.0, "unit_position": "cm", "cw": 0.0, "unit_cw": "mm", "ch": 0.0, "unit_ch": "mm"},
            {"id": "outlet", "label": "Coolant Outlet", "fixed": True, "position": 0.0, "unit_position": "cm", "cw": 0.0, "unit_cw": "mm", "ch": 0.0, "unit_ch": "mm"},
        ]
        self.next_control_point_id = 0

    # Sender function
    def get_control_points(self) -> list[dict]:
        return self.control_points

    def add_control_point(self, control_point_after_id: str):
        current_id = next(i for i, p in enumerate(self.control_points) if p["id"] == control_point_after_id)

        self.control_points.insert(current_id + 1, {
            "id": f"cp_{self.next_control_point_id}",
            "label": "Control Point",
            "fixed": False,
            "position": 0.0, "unit_position": "cm",
            "cw": 0.0, "unit_cw": "mm",
            "ch": 0.0, "unit_ch": "mm",
        })

        self.next_control_point_id += 1

    def delete_control_point(self, control_point_id: str):
        self.control_points = [p for p in self.control_points if p["id"] != control_point_id]

    def update_control_point_field(self, control_point_id: str, field: str, value):
        for point in self.control_points:
            if point["id"] == control_point_id:
                point[field] = value
                return
            

# Control Points Manager Instance
control_points_manager = ControlPointsInput()


# Live update nozzle canvas
def update_nozzle_canvas(state: dict):
    dpg.delete_item("nozzle_canvas", children_only=True)

    axial_positions_m = state["nozzle_parameters"]["x"]
    radii_m = state["nozzle_parameters"]["R_x"]

    ruler_width_px = 50
    margin_top_px = 5
    margin_right_px = 30
    margin_bottom_px = 40

    plot_origin_x_px = ruler_width_px
    plot_origin_y_px = margin_top_px

    axial_min_m, axial_max_m = float(min(axial_positions_m)), float(max(axial_positions_m))
    nozzle_length_m = axial_max_m - axial_min_m
    nozzle_max_radius_m = float(max(radii_m))

    window_size_px = dpg.get_item_rect_size("nozzle_canvas_window")
    canvas_width_px = window_size_px[0]

    if canvas_width_px == 0:
        return

    # Scale the drawing and canvas
    plot_width_px = canvas_width_px - ruler_width_px - margin_right_px
    plot_height_px = plot_width_px * nozzle_max_radius_m / nozzle_length_m
    canvas_height_px = int(plot_origin_y_px + plot_height_px + margin_bottom_px)

    dpg.configure_item("nozzle_canvas", width=canvas_width_px, height=canvas_height_px)

    px_per_m_axial = plot_width_px / nozzle_length_m
    px_per_m_radial = plot_height_px * 0.75 / nozzle_max_radius_m

    # Axis line
    axis_line_y_px = plot_origin_y_px + plot_height_px * 0.85

    def to_pixel(axial_m, radius_m):
        pixel_x = plot_origin_x_px + (axial_m - axial_min_m) * px_per_m_axial
        pixel_y = axis_line_y_px - radius_m * px_per_m_radial
        return pixel_x, pixel_y

    # Draw axis line
    dpg.draw_line((plot_origin_x_px, axis_line_y_px), (plot_origin_x_px + plot_width_px, axis_line_y_px), color=(100, 100, 100), thickness=1, parent="nozzle_canvas")

    # Draw nozzle contour
    contour_points_px = [to_pixel(axial_m, radius_m) for axial_m, radius_m in zip(axial_positions_m, radii_m)]
    dpg.draw_polyline(contour_points_px, color=(200, 200, 200), thickness=2, parent="nozzle_canvas")

    # Rulers
    _draw_ruler(
        start=(plot_origin_x_px, axis_line_y_px),
        length=nozzle_length_m,
        scale=px_per_m_axial,
        ticks=11,
        horizontal=True,
        parent="nozzle_canvas",
    )
    _draw_ruler(
        start=(ruler_width_px, axis_line_y_px),
        length=nozzle_max_radius_m,
        scale=px_per_m_radial,
        ticks=7,
        horizontal=False,
        parent="nozzle_canvas",
    )


# Ruler
def _draw_ruler(start, length, scale, ticks, horizontal, parent):

    step = length / ticks
    base_color = (180, 180, 180)
    end_color = (220, 180, 80)

    # Baseline
    if horizontal:
        dpg.draw_line(start, (start[0] + length * scale, start[1]), color=base_color, thickness=2, parent=parent)
    else:
        dpg.draw_line(start, (start[0], start[1] - length * scale), color=base_color, thickness=2, parent=parent)

    for i in range(ticks + 1):
        val = i * step
        is_end = i in (0, ticks)
        color = end_color if is_end else base_color
        size = 12 if is_end else 8

        if horizontal:
            x = start[0] + val * scale
            y = start[1]

            dpg.draw_line((x, y), (x, y + size), color=color, thickness=2, parent=parent)
            dpg.draw_text((x - 14, y + 12), f"{round(val * 100)}cm", size=13, color=color, parent=parent)

        else:
            x = start[0]
            y = start[1] - val * scale

            dpg.draw_line((x, y), (x - size, y), color=color, thickness=2, parent=parent)
            dpg.draw_text((5, y - 7), f"{round(val * 100)}cm", size=13, color=color, parent=parent)