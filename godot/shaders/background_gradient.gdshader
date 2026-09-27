shader_type canvas_item;

// icon.sys-style background: one colour per screen corner. The colours are sRGB and interpolate
// in sRGB, as on the PS2. 2D rendering is sRGB here, so no conversion is needed.
uniform vec3 top_left = vec3(0.106, 0.122, 0.290);
uniform vec3 top_right = vec3(0.106, 0.122, 0.290);
uniform vec3 bottom_left = vec3(0.016, 0.016, 0.047);
uniform vec3 bottom_right = vec3(0.043, 0.043, 0.141);

void fragment() {
	vec3 top = mix(top_left, top_right, UV.x);
	vec3 bottom = mix(bottom_left, bottom_right, UV.x);
	COLOR = vec4(mix(top, bottom, UV.y), 1.0);
}
