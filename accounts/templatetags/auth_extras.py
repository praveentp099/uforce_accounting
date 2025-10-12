from django import template

register = template.Library()

@register.filter(name='has_role')
def has_role(user, role_names):
    """
    Checks if a user's role is in a comma-separated list of roles.
    Usage in template: {% if user|has_role:'admin,owner' %}
    """
    if not hasattr(user, 'role'):
        return False
    
    # Split the provided string of role names into a list
    roles = [role.strip() for role in role_names.split(',')]
    
    return user.role in roles

