from flask import render_template
from . import admin_bp
from model import db, User, UserInteraction
from sqlalchemy import func, desc, extract
from datetime import datetime, timedelta

@admin_bp.route('/')
def admin_dashboard():
    total_users = User.query.count()

    # ✅ New Users This Week
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    new_users = User.query.filter(User.created_at >= one_week_ago).count()

    # ✅ Most Active Hours
    active_hours = (
        db.session.query(
            extract('hour', UserInteraction.timestamp).label('hour'),
            func.count().label('count')
        )
        .group_by('hour')
        .order_by('hour')
        .all()
    )

    # ✅ Interests by Hour (grouped)
    interest_by_hour = (
        db.session.query(
            extract('hour', UserInteraction.timestamp).label('hour'),
            UserInteraction.interest,
            func.count().label('count')
        )
        .group_by('hour', UserInteraction.interest)
        .order_by('hour')
        .all()
    )

    # Format active_hours for chart
    hour_labels = [f"{int(h):02d}:00" for h, _ in active_hours]
    hour_data = [count for _, count in active_hours]

    # Format interest_by_hour into structure:
    # {interest1: [counts], interest2: [counts], ...}
    interest_labels = sorted(set(i for _, i, _ in interest_by_hour))
    interest_data = {i: [0]*24 for i in interest_labels}
    for h, interest, count in interest_by_hour:
        interest_data[interest][int(h)] = count

    # Active users in last 24h
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    active_user_ids = (
        db.session.query(UserInteraction.user_id)
        .filter(UserInteraction.timestamp >= last_24h)
        .distinct()
        .all()
    )
    active_users_24h = len(active_user_ids)

    # Top Searched Interests
    most_searched_interests = (
        db.session.query(
            UserInteraction.interest,
            func.count().label('search_count')
        )
        .group_by(UserInteraction.interest)
        .order_by(desc('search_count'))
        .limit(5)
        .all()
    )
    interest_bar_labels = [row[0] for row in most_searched_interests]
    interest_bar_data = [row[1] for row in most_searched_interests]

    # Top Searched Pincodes
    most_searched_pincodes = (
        db.session.query(
            UserInteraction.pincode,
            func.count().label('search_count')
        )
        .group_by(UserInteraction.pincode)
        .order_by(desc('search_count'))
        .limit(5)
        .all()
    )
    pincode_labels = [row[0] for row in most_searched_pincodes]
    pincode_data = [row[1] for row in most_searched_pincodes]

    # Search Frequency Over Time
    search_freq = (
        db.session.query(
            func.date(UserInteraction.timestamp).label('date'),
            func.count().label('count')
        )
        .group_by(func.date(UserInteraction.timestamp))
        .order_by(func.date(UserInteraction.timestamp))
        .all()
    )
    freq_dates = [row[0].strftime('%Y-%m-%d') for row in search_freq]
    freq_counts = [row[1] for row in search_freq]

    # For Interest Searches by Hour (Stacked Bar Chart)
    interest_datasets = [
        {
            "label": interest,
            "data": interest_data[interest],
            "backgroundColor": f"hsl({i * 60}, 70%, 60%)"
        }
        for i, interest in enumerate(interest_labels)
    ]

    return render_template(
        'admin_dashboard.html',
        total_users=total_users,
        new_users=new_users,
        active_users_24h=active_users_24h,
        hour_labels=hour_labels,
        hour_data=hour_data,
        interest_labels=interest_labels,
        interest_data=interest_data,
        interest_bar_labels=interest_bar_labels,
        interest_bar_data=interest_bar_data,
        pincode_labels=pincode_labels,
        pincode_data=pincode_data,
        freq_dates=freq_dates,
        freq_counts=freq_counts,
        interest_datasets=interest_datasets
    )
