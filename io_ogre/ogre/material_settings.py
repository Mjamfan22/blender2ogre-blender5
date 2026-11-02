"""Current Blender material settings for OGRE (LGPL 2.1 or later)."""


def alpha_mode(material, wrapper):
    """Render method alone cannot distinguish opaque from translucent in 4.2+."""
    explicit = material.get('ogre_alpha_mode', 'AUTO')
    if explicit in ('OPAQUE', 'MASK', 'BLEND'):
        return explicit
    node = wrapper.node_principled_bsdf
    alpha = node.inputs.get('Alpha') if node else None
    return 'BLEND' if wrapper.alpha < 1 or (alpha and alpha.is_linked) else 'OPAQUE'


def alpha_threshold(material):
    return max(0, min(1, float(material.get('ogre_alpha_threshold', 0.5))))
