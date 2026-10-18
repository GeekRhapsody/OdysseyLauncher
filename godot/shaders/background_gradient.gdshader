shader_type canvas_item;

// icon.sys-style background: one colour per screen corner. The colours are sRGB and interpolate
// in sRGB, as on the PS2. 2D rendering is sRGB here, so no conversion is needed.
uniform vec3 top_left = vec3(0.106, 0.122, 0.290);
uniform vec3 top_right = vec3(0.106, 0.122, 0.290);
uniform vec3 bottom_left = vec3(0.016, 0.016, 0.047);
uniform vec3 bottom_right = vec3(0.043, 0.043, 0.141);

// Up to two wallpapers over the gradient (A6 Background), cross-fading as the look does: (A's weight, B's weight,
// A's width over its height, B's), an aspect of 0 or less stretching the image to the screen. The weights never sum
// past 1, and each image's own alpha scales its weight, so a transparent one shows the gradient. Sampled raw: sRGB,
// as the gradient is. item.gdshader's backdrop() must stay the same, so items fade into exactly this.
uniform sampler2D wallpaper_a : filter_linear, repeat_disable;
uniform sampler2D wallpaper_b : filter_linear, repeat_disable;
uniform vec4 wallpaper_state = vec4(0.0);

// The image's UV for a screen UV: cropped evenly to cover the screen, or stretched over it.
vec2 cover(vec2 uv, float image_aspect, float screen_aspect) {
	if (image_aspect <= 0.0) {
		return uv;
	}
	return image_aspect > screen_aspect
		? vec2(0.5 + (uv.x - 0.5) * screen_aspect / image_aspect, uv.y)
		: vec2(uv.x, 0.5 + (uv.y - 0.5) * image_aspect / screen_aspect);
}

void fragment() {
	vec3 top = mix(top_left, top_right, UV.x);
	vec3 bottom = mix(bottom_left, bottom_right, UV.x);
	vec3 colour = mix(top, bottom, UV.y);
	if (wallpaper_state.x + wallpaper_state.y > 0.0) {
		float screen_aspect = SCREEN_PIXEL_SIZE.y / SCREEN_PIXEL_SIZE.x;
		vec4 a = textureLod(wallpaper_a, cover(UV, wallpaper_state.z, screen_aspect), 0.0);
		vec4 b = textureLod(wallpaper_b, cover(UV, wallpaper_state.w, screen_aspect), 0.0);
		float wa = a.a * wallpaper_state.x;
		float wb = b.a * wallpaper_state.y;
		colour = colour * (1.0 - wa - wb) + a.rgb * wa + b.rgb * wb;
	}
	COLOR = vec4(colour, 1.0);
}
