"""Rebuild every generated model in the right order: apartment -> human -> robot.   Run: python src/sim/build_all.py"""
import build_apartment
import build_human_mjcf
import build_robot_mjcf

if __name__ == "__main__":
    build_apartment.build()
    build_human_mjcf.build()
    build_robot_mjcf.build()
