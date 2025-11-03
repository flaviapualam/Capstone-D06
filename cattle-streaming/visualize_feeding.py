#!/usr/bin/env python3
"""
Visual comparison of feeding patterns.
Generates analysis charts for Current vs Realistic behavior.
"""

import random


def simulate_feeding_day(mode="current"):
    """Simulate one day of feeding and return hopper levels over time."""
    
    if mode == "current":
        # Current parameters
        feed_per_pulse = 6  # kg
        session_duration_sec = 8 * 60  # 8 minutes
        eating_rate_kg_per_sec = 2.0 / 3600.0  # 2 kg/hr
        sessions_per_pulse = 1
    else:  # realistic
        # Realistic parameters
        feed_per_pulse = 10  # kg
        session_duration_sec = 30 * 60  # 30 minutes
        eating_rate_kg_per_sec = 20.0 / 3600.0  # 20 kg/hr
        sessions_per_pulse = 1
    
    hopper_timeline = []
    current_hopper = 0
    time_min = 0
    
    # 08:00 pulse (28800 sec = 480 min from midnight)
    for _ in range(sessions_per_pulse):
        current_hopper = feed_per_pulse
        
        for sec in range(session_duration_sec):
            current_hopper = max(0, current_hopper - eating_rate_kg_per_sec)
            time_min = 480 + (sec / 60.0)  # 08:00 in minutes from midnight
            hopper_timeline.append((time_min, current_hopper, "morning"))
    
    # Gap: 08:30 to 14:00
    gap_start_min = 480 + (session_duration_sec / 60.0)
    gap_end_min = 840  # 14:00 in minutes from midnight
    
    # Hopper decays slowly (oxidation, etc)
    for min_point in range(int(gap_start_min), int(gap_end_min), 10):
        hopper_timeline.append((min_point, current_hopper, "gap"))
    
    # 14:00 pulse
    for _ in range(sessions_per_pulse):
        current_hopper = feed_per_pulse
        
        for sec in range(session_duration_sec):
            current_hopper = max(0, current_hopper - eating_rate_kg_per_sec)
            time_min = 840 + (sec / 60.0)  # 14:00 in minutes from midnight
            hopper_timeline.append((time_min, current_hopper, "afternoon"))
    
    return hopper_timeline


def print_timeline_ascii(timeline, title):
    """Print ASCII chart of hopper over time."""
    
    print(f"\n{title}")
    print("=" * 80)
    
    if not timeline:
        print("No data")
        return
    
    # Get time range and max weight
    times = [t[0] for t in timeline]
    weights = [t[1] for t in timeline]
    max_weight = max(weights) if weights else 10
    
    # Print header with times
    hours_str = ""
    prev_hour = -1
    for t in times[::len(times)//10]:  # Sample every 10%
        h = int(t / 60)
        if h != prev_hour:
            hours_str += f"{h:02d}:00  "
            prev_hour = h
    
    print(f"Weight vs Time")
    print(f"Max weight: {max_weight:.1f} kg")
    print()
    
    # Print chart
    height = 20  # lines
    for level in range(height, -1, -1):
        weight_threshold = (level / height) * max_weight
        
        line = f"{weight_threshold:5.1f} kg │"
        
        for t, w, phase in timeline[::max(1, len(timeline)//80)]:  # Sample for width
            if w >= weight_threshold:
                if phase == "morning":
                    line += "█"
                elif phase == "afternoon":
                    line += "▓"
                else:
                    line += "░"
            else:
                line += " "
        
        print(line)
    
    print("        └" + "─" * 80)
    print("        08:00        10:00        12:00        14:00        16:00")
    print()


def print_statistics(timeline, mode):
    """Print statistics about the feeding pattern."""
    
    morning_weights = [w for t, w, p in timeline if p == "morning"]
    afternoon_weights = [w for t, w, p in timeline if p == "afternoon"]
    
    print(f"\n{mode.upper()} MODE STATISTICS:")
    print("-" * 50)
    
    if morning_weights:
        print(f"Morning session:")
        print(f"  Start weight: {morning_weights[0]:.2f} kg")
        print(f"  End weight: {morning_weights[-1]:.2f} kg")
        print(f"  Consumed: {morning_weights[0] - morning_weights[-1]:.2f} kg")
        print(f"  % consumed: {((morning_weights[0] - morning_weights[-1]) / morning_weights[0] * 100):.1f}%")
        print(f"  Duration: ~30 min" if mode == "realistic" else "  Duration: ~8 min")
    
    if afternoon_weights:
        print(f"\nAfternoon session:")
        print(f"  Start weight: {afternoon_weights[0]:.2f} kg")
        print(f"  End weight: {afternoon_weights[-1]:.2f} kg")
        print(f"  Consumed: {afternoon_weights[0] - afternoon_weights[-1]:.2f} kg")
        print(f"  % consumed: {((afternoon_weights[0] - afternoon_weights[-1]) / afternoon_weights[0] * 100):.1f}%")
    
    # Overall
    all_weights = [w for t, w, p in timeline]
    print(f"\nDaily statistics:")
    print(f"  Max weight: {max(all_weights):.2f} kg")
    print(f"  Min weight: {min(all_weights):.2f} kg")
    print(f"  Total consumed: {max(all_weights) - min(all_weights):.2f} kg")


def main():
    """Generate visual comparison."""
    
    print("\n" + "=" * 80)
    print("CATTLE FEEDING PATTERN: VISUAL COMPARISON")
    print("=" * 80)
    
    # Current mode
    current_timeline = simulate_feeding_day("current")
    print_timeline_ascii(current_timeline, "CURRENT MODE (5-7 kg, 5-10 min, 0-2 kg/hr)")
    print_statistics(current_timeline, "current")
    
    print("\n" + "=" * 80)
    
    # Realistic mode
    realistic_timeline = simulate_feeding_day("realistic")
    print_timeline_ascii(realistic_timeline, "REALISTIC MODE (8-12 kg, 20-40 min, 18-24 kg/hr)")
    print_statistics(realistic_timeline, "realistic")
    
    print("\n" + "=" * 80)
    print("INTERPRETATION")
    print("=" * 80)
    print("""
CURRENT MODE (█ = morning, ▓ = afternoon, ░ = gap)
→ Weight drops VERY SLOWLY
→ Only ~5% consumed per session
→ Most feed wasted
→ Not realistic but good for testing flow

REALISTIC MODE
→ Weight drops to ZERO quickly
→ ~90-100% consumed per session
→ Meal completion visible
→ Matches real dairy cow behavior
    """)


if __name__ == "__main__":
    main()
