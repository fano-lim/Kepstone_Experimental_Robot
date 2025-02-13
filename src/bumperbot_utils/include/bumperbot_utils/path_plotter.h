#ifndef PATH_PLOTTER_H
#define PATH_PLOTTER_H
#include <ros/ros.h>
#include <geometry_msgs/PoseWithCovarianceStamped.h>
#include <nav_msgs/Odometry.h>
#include <nav_msgs/Path.h>

class PathPlotter
{
public:
    PathPlotter(const ros::NodeHandle &);

private:
    ros::NodeHandle nh_;
    ros::Subscriber odom_sub_;
    ros::Publisher trajectory_pub_;
    nav_msgs::Path path;  

    std::vector<geometry_msgs::PoseStamped> poses;

    void amclCallback(const geometry_msgs::PoseWithCovarianceStamped&);
};

#endif