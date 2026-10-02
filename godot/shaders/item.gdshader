shader_type spatial;
render_mode cull_back, depth_draw_opaque;

// The launcher's one shader for grid items (ARCHITECTURE.md A3, A7): one draw call per template MultiMesh, opaque,
// no variants. Every model is remapped onto it (Models/ModelConverter.cs):
//   COLOR     = the material's base colour (linear) and roughness
//   UV        = the face's own UV (0..1 across a slot face, upright seen from outside)
//   UV2       = (face code, the face's width over its height), where the face code is
//               (media slot + 1) * 8 + (authored texture + 1), 0 meaning none in either part
// Each instance carries INSTANCE_CUSTOM (or, drawn as its own node, node_custom: a per-game model, or a model playing a
// clip) =
//   r: the pool cell, which picks its row of slot_state and its place in the title atlas
//   g: the plain colour of a box with no art (or of a system card), sRGB packed as r * 65536 + g * 256 + b
//   b: the idle phase, or -1 when focused
//   a: 1 when an idle clip animates it, so it doesn't bob as well
// and slot_state holds, per cell (y) and media slot (x): what the slot shows without media (1 generated,
// 0 authored; plus 2 when the spine shows a logo, drawn whole along it over that), the media's aspect (0 when none is
// wanted), its fade in, and its layer. Two more columns per cell reshape a box to its game's art (A6 shape = "media"):
// SHAPE_COLUMN = (half the width's growth, the height's, half the depth's, the height where the top half starts; all 0
// for every other model), then (the front and back faces' aspect, the spine's).
// (Godot 4 multiplies a MultiMesh's instance colour into COLOR, which carries the material data here.)

// Media slots, in Launcher.Core.Theming.MediaSlots order.
const int SLOT_COVER = 0;
const int SLOT_BACK = 1;
const int SLOT_SPINE = 2;
const int SLOT_LABEL = 4;
const int SHAPE_COLUMN = 8;

// Media, one layer per pool cell and slot channel, BC7 with mips. The whole image is squeezed into the square and
// cropped here to the face. The cover's layers are 512²; every other slot's are 256² (Grid/SlotLayout.cs).
uniform sampler2DArray slots_large : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2DArray slots_small : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D slot_state : filter_nearest, repeat_disable;

// INSTANCE_CUSTOM for an item drawn as its own node (Grid/ItemGrid.cs); a MultiMesh leaves it at -1 and uses its own.
instance uniform vec4 node_custom = vec4(-1.0, 0.0, 0.0, 0.0);

// The template's own textures, as its materials were authored (a slot's last fallback, or a plain material's).
uniform sampler2D authored_1 : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D authored_2 : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D authored_3 : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D authored_4 : source_color, filter_linear_mipmap_anisotropic, repeat_enable;

// Titles, drawn by a SubViewport (Grid/TitleAtlas.cs): a square block per cell, and a strip per cell for spines.
// Only the alpha is used.
uniform sampler2D titles : filter_linear, repeat_disable;
uniform vec2 block_size = vec2(0.125);
uniform int block_columns = 8;
uniform vec2 spine_origin = vec2(0.6, 0.0);
uniform vec2 spine_size = vec2(0.2, 0.02);
uniform int spine_columns = 2;

// 0 = drawn normally, 1 = exactly the background behind it: transitions fade whole grids without blending.
uniform float grid_fade = 0.0;
// Items fade towards the background near the top and bottom of the screen, under the overlay's text:
// (top band, bottom band, strength), in screen fractions.
uniform vec3 edge_fade = vec3(0.2, 0.22, 0.8);
// A system card's plain materials take its system's colour.
uniform bool tint_case = false;

// The four background corners, sRGB, as on the canvas layer behind the scene (they cross-fade with the look).
uniform vec3 bg_top_left = vec3(0.106, 0.122, 0.290);
uniform vec3 bg_top_right = vec3(0.106, 0.122, 0.290);
uniform vec3 bg_bottom_left = vec3(0.016, 0.016, 0.047);
uniform vec3 bg_bottom_right = vec3(0.043, 0.043, 0.141);

varying flat float v_cell;
varying flat int v_slot;
varying flat int v_tex;
varying flat vec4 v_state;
varying flat vec4 v_cover;
varying flat float v_focus;
varying flat vec3 v_plain;
varying flat vec3 v_dominant;
varying flat vec3 v_ink;
varying flat float v_face_aspect;
varying flat vec3 v_base;
varying flat float v_roughness;

vec3 to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

float luminance(vec3 c) {
	return dot(c, vec3(0.2126, 0.7152, 0.0722));
}

// The most common colour of the cover, from its 4x4 mip: each texel scores the texels close to it, and saturated
// colours are preferred over greys, so a mostly white cover with a red logo still gives a red spine.
vec3 dominant_colour(float layer) {
	vec3 c[16];
	for (int i = 0; i < 16; i++) {
		vec2 uv = (vec2(float(i % 4), float(i / 4)) + 0.5) / 4.0;
		c[i] = sqrt(textureLod(slots_large, vec3(uv, layer), 7.0).rgb);
	}
	vec3 best = c[0];
	float best_score = -1.0;
	for (int i = 0; i < 16; i++) {
		float score = 0.0;
		for (int j = 0; j < 16; j++) {
			score += max(0.0, 1.0 - distance(c[i], c[j]) * 4.0);
		}
		float saturation = max(c[i].r, max(c[i].g, c[i].b)) - min(c[i].r, min(c[i].g, c[i].b));
		score *= 0.6 + saturation;
		if (score > best_score) {
			best_score = score;
			best = c[i];
		}
	}
	return best * best;
}

void vertex() {
	vec4 custom = node_custom.r >= 0.0 ? node_custom : INSTANCE_CUSTOM;
	v_cell = floor(custom.r + 0.5);
	int cell = int(v_cell);
	int code = int(UV2.x + 0.5);
	v_slot = code / 8 - 1;
	v_tex = code % 8 - 1;
	v_face_aspect = UV2.y;
	v_state = v_slot >= 0 ? texelFetch(slot_state, ivec2(v_slot, cell), 0) : vec4(0.0);

	// A box shaped by its game's art: each half of the rest mesh moves out (or in) by the growth, so bevels and corners
	// keep their size and flat faces their normals, and the faces take the art's proportions, so it isn't cropped.
	vec4 shape = texelFetch(slot_state, ivec2(SHAPE_COLUMN, cell), 0);
	if (shape.w > 0.0) {
		VERTEX.x += sign(VERTEX.x) * shape.x;
		VERTEX.z += sign(VERTEX.z) * shape.z;
		VERTEX.y += step(shape.w, VERTEX.y) * shape.y;
		vec2 faces = texelFetch(slot_state, ivec2(SHAPE_COLUMN + 1, cell), 0).xy;
		if (v_slot == SLOT_COVER || v_slot == SLOT_BACK) {
			v_face_aspect = faces.x;
		} else if (v_slot == SLOT_SPINE) {
			v_face_aspect = faces.y;
		}
	}
	v_cover = texelFetch(slot_state, ivec2(SLOT_COVER, cell), 0);
	v_focus = custom.b < 0.0 ? 1.0 : 0.0;
	float packed = custom.g;
	v_plain = to_linear(vec3(floor(packed / 65536.0), mod(floor(packed / 256.0), 256.0), mod(packed, 256.0)) / 255.0);
	v_base = COLOR.rgb;
	v_roughness = COLOR.a;

	// Unfocused items bob gently, unless an idle clip animates them (A7); it costs nothing on the CPU (A3).
	if (custom.b >= 0.0 && custom.a < 0.5) {
		VERTEX.y += sin(TIME * 1.3 + custom.b) * 0.012;
	}

	// A generated spine or back takes its colour from the cover once the cover's art is there.
	v_dominant = v_plain;
	if ((v_slot == SLOT_SPINE || v_slot == SLOT_BACK) && mod(v_state.x, 2.0) > 0.5 && v_cover.y > 0.0 && v_cover.z > 0.0) {
		v_dominant = mix(v_plain, dominant_colour(v_cover.w), v_cover.z);
	}
	v_ink = luminance(v_dominant) > 0.3 ? vec3(0.02) : vec3(0.92);
}

// Centre-crops art of aspect `art` to fill a face of aspect `face`.
vec2 crop(vec2 uv, float art, float face) {
	if (art > face) {
		uv.x = 0.5 + (uv.x - 0.5) * face / art;
	} else {
		uv.y = 0.5 + (uv.y - 0.5) * art / face;
	}
	return uv;
}

// The title block's coverage at a rectangle of the face: `rect` is (u0, v0, width in u); the block is square on the
// face, so its height in v is its width times the face's aspect.
float title_block(vec2 uv, vec3 rect, float face_aspect) {
	vec2 local = vec2((uv.x - rect.x) / rect.z, (uv.y - rect.y) / (rect.z * face_aspect));
	if (any(lessThan(local, vec2(0.0))) || any(greaterThan(local, vec2(1.0)))) {
		return 0.0;
	}
	int cell = int(v_cell);
	vec2 origin = vec2(float(cell % block_columns), float(cell / block_columns)) * block_size;
	return texture(titles, origin + local * block_size).a;
}

// The spine strip's coverage: the text reads top to bottom, with the tops of the letters towards the front.
float title_spine(vec2 uv) {
	vec2 local = vec2(uv.y, 1.0 - uv.x);
	int cell = int(v_cell);
	vec2 origin = spine_origin + vec2(float(cell % spine_columns), float(cell / spine_columns)) * spine_size;
	return texture(titles, origin + clamp(local, vec2(0.002), vec2(0.998)) * spine_size).a;
}

// A box with no art: the plain colour, lighter at the top, with a thin inset frame.
vec3 plain_face(vec2 uv, vec3 colour) {
	vec3 shaded = colour * mix(1.25, 0.7, uv.y);
	vec2 edge = min(uv, 1.0 - uv);
	float frame = step(0.035, edge.x) * step(0.035 * v_face_aspect, edge.y) * (1.0 - step(0.045, edge.x) * step(0.045 * v_face_aspect, edge.y));
	return mix(shaded, colour * 1.6 + 0.04, frame * 0.6);
}

// The material's own texture (or its base colour alone).
vec3 authored(vec2 uv) {
	vec3 texel = vec3(1.0);
	if (v_tex == 0) {
		texel = texture(authored_1, uv).rgb;
	} else if (v_tex == 1) {
		texel = texture(authored_2, uv).rgb;
	} else if (v_tex == 2) {
		texel = texture(authored_3, uv).rgb;
	} else if (v_tex == 3) {
		texel = texture(authored_4, uv).rgb;
	}
	return v_base * texel;
}

// The slot's media, cropped to the face.
vec3 media(vec2 uv, float face_aspect) {
	vec3 coord = vec3(crop(uv, v_state.y, face_aspect), v_state.w);
	return v_slot == SLOT_COVER ? texture(slots_large, coord).rgb : texture(slots_small, coord).rgb;
}

// A logo on the spine: whole, reading top to bottom like the spine's title, over the spine's fallback: its authored
// texture, or for a generated fallback the cover's colour darkened to a deep shade, since logos are made to sit on
// dark art (their light parts often have only a dark outline).
vec3 logo_spine(vec2 uv, float face_aspect) {
	vec3 base = authored(uv);
	if (mod(v_state.x, 2.0) > 0.5) {
		base = v_dominant * min(0.9, 0.04 / max(luminance(v_dominant), 0.001));
	}

	// Along the spine, with a margin: the logo fills at most 90% of its length and 76% of its depth.
	const vec2 FILL = vec2(0.9, 0.76);
	vec2 p = (vec2(uv.y, 1.0 - uv.x) - 0.5) / FILL;
	float box = FILL.x / (FILL.y * face_aspect);
	float art = max(v_state.y, 0.01);
	if (art > box) {
		p.y *= art / box;
	} else {
		p.x *= box / art;
	}
	p += 0.5;
	if (any(lessThan(p, vec2(0.0))) || any(greaterThan(p, vec2(1.0)))) {
		return base;
	}
	vec4 logo = texture(slots_small, vec3(p, v_state.w));
	return mix(base, logo.rgb, logo.a);
}

// The faces the launcher draws itself (M5): a title card for the cover (dim and untitled while its art loads), a spine
// and back in the cover's colour with the title, and a paper label with the title.
vec3 generated(vec2 uv, float face_aspect, bool loading, out float roughness) {
	roughness = v_roughness;
	if (v_slot == SLOT_COVER) {
		vec3 plain = plain_face(uv, v_plain);
		if (loading) {
			return plain * 0.6;
		}
		float ink = title_block(uv, vec3(0.1, 0.5 - 0.4 * face_aspect, 0.8), face_aspect);
		return mix(plain, vec3(0.95), ink);
	}
	if (v_slot == SLOT_SPINE) {
		vec3 base = v_dominant * 0.9;
		// A darker band at the top, where a real spine carries the platform's logo.
		base *= uv.y < 0.1 ? 0.3 : 1.0;
		return mix(base, v_ink, title_spine(uv));
	}
	if (v_slot == SLOT_BACK) {
		vec3 base = v_dominant * mix(0.6, 0.3, uv.y);
		float ink = title_block(uv, vec3(0.15, 0.04, 0.7), face_aspect);
		vec3 back = mix(base, v_ink, ink);
		// A strip of the cover in the lower half, as a back's screenshots would be.
		vec4 strip = vec4(0.1, 0.56, 0.9, 0.92);
		if (v_cover.y > 0.0 && uv.x > strip.x && uv.x < strip.z && uv.y > strip.y && uv.y < strip.w) {
			vec2 local = (uv - strip.xy) / (strip.zw - strip.xy);
			float strip_aspect = (strip.z - strip.x) / ((strip.w - strip.y) / face_aspect);
			vec3 art = texture(slots_large, vec3(crop(local, v_cover.y, strip_aspect), v_cover.w)).rgb;
			back = mix(back, art, v_cover.z);
		}
		return back;
	}
	if (v_slot == SLOT_LABEL) {
		vec3 paper = mix(vec3(0.86, 0.87, 0.9), v_plain, 0.12);
		float ink = title_block(uv, vec3(0.06, 0.5 - 0.44 * face_aspect, 0.88), face_aspect);
		roughness = 0.6;
		return mix(paper, vec3(0.03, 0.035, 0.06), ink);
	}
	return authored(uv);
}

void fragment() {
	vec3 albedo;
	float roughness = v_roughness;
	vec2 uv = UV;
	float face_aspect = max(v_face_aspect, 0.01);

	if (v_slot < 0) {
		albedo = authored(uv);
		if (tint_case) {
			albedo = mix(albedo, v_plain, 0.85);
		}
	} else {
		bool wants_media = v_state.y > 0.0;
		vec3 fallback = mod(v_state.x, 2.0) > 0.5 ? generated(uv, face_aspect, wants_media, roughness) : authored(uv);
		// Opaque fallback-to-media fade inside the one shader (A3): no blending, no extra variant.
		if (wants_media) {
			vec3 shown = v_state.x > 1.5 ? logo_spine(uv, face_aspect) : media(uv, face_aspect);
			albedo = mix(fallback, shown, v_state.z);
		} else {
			albedo = fallback;
		}
	}

	// The focused item glows a little, as the PS2 browser's selection does.
	vec3 emission = albedo * 0.18 * v_focus;

	vec3 background = to_linear(mix(
		mix(bg_top_left, bg_top_right, SCREEN_UV.x),
		mix(bg_bottom_left, bg_bottom_right, SCREEN_UV.x),
		SCREEN_UV.y));
	float edge = max(1.0 - smoothstep(0.0, edge_fade.x, SCREEN_UV.y), smoothstep(1.0 - edge_fade.y, 1.0, SCREEN_UV.y));
	float fade = max(grid_fade, edge * edge_fade.z);
	ALBEDO = albedo * (1.0 - fade);
	ROUGHNESS = roughness;
	SPECULAR = 0.5 * (1.0 - fade);
	EMISSION = mix(emission, background, fade);
}
