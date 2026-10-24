#!/usr/bin/env python
"""
Quick script to create a superuser for NovaChrono admin access.
Usage: python create_admin_user.py <email> <password> [name]
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'novachrono.settings')
django.setup()

from django.contrib.auth import get_user_model

def create_superuser(email, password, name="Admin"):
    """Create a superuser with the given credentials."""
    User = get_user_model()
    
    try:
        if User.objects.filter(email=email).exists():
            print(f"⚠️  User with email '{email}' already exists!")
            user = User.objects.get(email=email)
            if user.is_superuser:
                print(f"   User is already a superuser.")
                return user
            else:
                user.is_superuser = True
                user.is_staff = True
                user.status = 'active'
                user.save()
                print(f"   ✓ Promoted existing user to superuser!")
                return user
        
        # Create new user
        user = User()
        user.email = email
        user.username = email  # username mirrors email in this project
        user.name = name
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.status = 'active'
        user.save()
        
        print(f"✅ Superuser created successfully!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Name: {name}")
        return user
        
    except Exception as e:
        print(f"❌ Error creating superuser: {e}")
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python create_admin_user.py <email> <password> [name]")
        print("Example: python create_admin_user.py admin@yourdomain.com password123 'Admin User'")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else "Admin"
    
    print("🔧 Creating NovaChrono admin superuser...")
    create_superuser(email, password, name)
    print(f"\n🌐 Admin dashboard: http://localhost:8000/admin/")
    print(f"🔐 Custom admin area: http://localhost:8000/admin/dashboard/")