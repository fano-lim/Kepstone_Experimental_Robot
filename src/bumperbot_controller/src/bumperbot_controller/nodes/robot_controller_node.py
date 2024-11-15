import rospy
from geometry_msgs.msg import Point
from std_msgs.msg import String
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from actionlib import SimpleActionClient, GoalStatus
from enum import Enum
from bumperbot_detection.msg import LitterPoint 
from std_srvs.srv import SetBool, Trigger
from navigation.srv import InitiateCoveragePath, InitiateCoveragePathRequest, InitiateCoveragePathResponse
from navigation.srv import GetNextWaypoint, GetNextWaypointResponse
from litter_destruction.srv import GlobalBoundaryCenter, GlobalBoundaryCenterResponse
from litter_destruction.srv import GetNextLitter
from litter_destruction.srv import RemoveLitter, RemoveLitterRequest 
from litter_destruction.srv import HasLitterToClear
from litter_destruction.srv import GetNextTargetLitter, GetNextTargetLitterResponse
from bumperbot_controller.srv import ModeSwitch, ModeSwitchResponse
from bumperbot_controller.srv import GetCurrentMode, GetCurrentModeResponse
import threading


# Enum for robot modes
class RobotMode(Enum):
    IDLE               = 1
    COVERAGE           = 2
    LITTER_PICKING     = 3
    LITTER_TO_COVERAGE = 4


class RobotController:
    def __init__(self):
        self.litter_picking_waypoint_service = '/litter_manager/next_waypoint'
        self.coverage_path_waypoint_service  = '/coverage_path/next_waypoint'

        ## Configurations
        # ROS action client for move_base
        self.move_base_client = SimpleActionClient('move_base', MoveBaseAction)
        self.move_base_client.wait_for_server()

        self.mode = RobotMode.IDLE
        self.coverage_complete = False  # Flag to track if coverage is complete
        self.global_boundary_center = Point()
        self.global_boundary_radius = 0

        ## Publishers

        ## Subscribers
        # Subscriptions to the waypoint topics for each mode

        # Services servers to initialise first for controllers to start (Dependencies caused by wait_for_service)
        rospy.Service('/robot_controller/mode_switch', ModeSwitch, self.handle_mode_switch)                                         # Service server to request mode switch
        rospy.Service('/robot_controller/get_global_boundary_center', GlobalBoundaryCenter, self.handle_get_global_boundary_center) # Service server to get global boundary center of robot controller

        ## Service Clients
        rospy.wait_for_service('/waypoint_manager/get_next_waypoint')
        rospy.wait_for_service('/waypoint_manager/initiate_coverage_path')
        rospy.wait_for_service('/litter_manager/get_global_boundary_center')
        rospy.wait_for_service('/litter_manager/get_next_litter')
        rospy.wait_for_service('/litter_manager/delete_litter')
        rospy.wait_for_service('/litter_manager/has_litter_to_clear')
        rospy.wait_for_service(self.litter_picking_waypoint_service)
        rospy.wait_for_service(self.coverage_path_waypoint_service)
        rospy.wait_for_service('/republish_global_boundary')

        self.update_waypoint_status = rospy.ServiceProxy('/waypoint_manager/get_next_waypoint', SetBool)                                     # Service to update waypoint_manager (get next waypoint)
        self.initiate_coverage_path = rospy.ServiceProxy('/waypoint_manager/initiate_coverage_path', InitiateCoveragePath)                   # Service to initate the coverage path   
        self.get_global_boundary_center_service = rospy.ServiceProxy('/litter_manager/get_global_boundary_center', GlobalBoundaryCenter)     # Service to get global boundary center
        self.get_next_litter = rospy.ServiceProxy('/litter_manager/get_next_litter', GetNextLitter)                                          # Service to update to next litter in litter manager 
        self.delete_litter   = rospy.ServiceProxy('/litter_manager/delete_litter', RemoveLitter)                                             # Service to delete litter in litter manager
        self.has_litter_to_clear = rospy.ServiceProxy('/litter_manager/has_litter_to_clear', HasLitterToClear)                               # Service to check if any more litter to clear (litter manager)
        self.next_target_litter = rospy.ServiceProxy(self.litter_picking_waypoint_service, GetNextTargetLitter)                              # Service to get next target litter
        self.next_target_coverage_waypoint = rospy.ServiceProxy(self.coverage_path_waypoint_service, GetNextWaypoint)                        # Service to get next target waypoint for coverage
        self.republish_global_boundary = rospy.ServiceProxy('/republish_global_boundary', Trigger)

        ## Service Servers
        rospy.Service('/robot_controller/get_current_mode', GetCurrentMode, self.handle_get_current_mode)            # Service server to request current mode
        rospy.Service('/robot_controller/initiate_coverage', InitiateCoveragePath, self.handle_initiate_coverage)    # Service server to initiate coverage


    def handle_initiate_coverage(self, req):
        """Service handler to initiate coverage path"""
        response = InitiateCoveragePathResponse()
        try:
            # Set the waypoints file path
            request = InitiateCoveragePathRequest(waypoints_file=req.waypoints_file)

            # Call the service to initiate coverage
            service_response = self.initiate_coverage_path(request)

            if service_response.success:
                rospy.loginfo("Coverage path initiated successfully.")
                response.success = True
                response.message = "Coverage path successfully initiated."

                # Set mode to COVERAGE if initiation was successful
                self.switch_mode(RobotMode.COVERAGE)
            else:
                rospy.logwarn(f"Coverage path initiation failed: {service_response.message}")
                response.success = False
                response.message = f"Failed to initiate coverage path: {service_response.message}"

        except rospy.ServiceException as e:
            rospy.logerr(f"Service call to initiate coverage path failed: {e}")
            response.success = False
            response.message = f"Service call failed: {e}"

        return response
    

    def handle_get_global_boundary_center(self, req):
        """Service handle to get global boundary center"""
        response = GlobalBoundaryCenterResponse()
        if self.global_boundary_center:
            response.center = self.global_boundary_center
            response.radius = self.global_boundary_radius
            response.valid = True
        else:
            response.center = Point()
            response.valid = False
        return response


    def handle_get_current_mode(self, req):
        """Service handler to get current mode of robot controller"""
        response = GetCurrentModeResponse()
        try:
            response.mode = self.mode.value
            response.success = True
        except:
            response.mode = -1
            response.success = False
        return response


    def handle_mode_switch(self, req):
        """Service handler to switch mode (RobotMode enum)"""
        response = ModeSwitchResponse()
        try:
            # Map the integer request to a RobotMode, raising an error if invalid
            if req.mode in RobotMode._value2member_map_:     # Check if in RobotMode
                self.switch_mode(RobotMode(req.mode))
                response.success = True
                response.message = f"Switched to {RobotMode(req.mode).name} mode."
            else:
                raise ValueError("Invalid mode requested.")
        except Exception as e:
            response.success = False
            response.message = str(e)
            rospy.logwarn(response.message) 
        return response
    

    def switch_mode(self, mode):
        """Switch the robot's mode and update the mux topic selection."""
        #######################################
        # PRE-CONDITIONS before switching modes
        #######################################
        # Check if robot is in transitioning mode to the center when asked to do litter picking (LITTER_TO_COVERAGE mode)
        if mode == RobotMode.LITTER_PICKING:
            if not self.mode == RobotMode.LITTER_TO_COVERAGE:
                # Still in transition, then if we detect litter then we shall clear it but dont change global center
                # O.w then we change the global center
                # Set global center
                if not self.get_global_boundary_center():
                    rospy.logerr("Failed to retrieve global boundary's center while changing to LITTER_PICKING mode")

        ######################
        # MODE switching logic
        ######################
        # Set new mode
        self.mode = mode

        # Trigger the global boundary visualization
        response = self.republish_global_boundary()
        
        # Determining topic based on mode and start the appropriate mode function
        if mode == RobotMode.IDLE:
            rospy.loginfo("Switched to IDLE mode.")

        elif mode == RobotMode.COVERAGE:
            # First call to set coverage to not complete
            self.coverage_complete = False

            # Prioritise LITTER_PICKING mode before switching to COVERAGE
            if self.has_litter_to_clear().has_litter:
                self.move_base_client.cancel_all_goals()
                self.switch_mode(RobotMode.LITTER_PICKING)
                return    
            rospy.loginfo("Switched to COVERAGE mode.")

            self.perform_coverage_mode() 

            # Monitor completion of coverage task and switch to IDLE if complete
            if self.is_coverage_complete():
                rospy.loginfo("Coverage task completed. Switching to IDLE mode.")
                self.switch_mode(RobotMode.IDLE)
                return

        elif mode == RobotMode.LITTER_PICKING:
            # Interrupt all other move goal to prioritise LITTER_PICKING
            self.move_base_client.cancel_all_goals()


            if response.success:
                rospy.loginfo("Global boundary marker published.")
            else:
                rospy.logwarn(f"Failed to publish global boundary marker: {response.message}")        

            # No more litter to clear
            if not self.has_litter_to_clear().has_litter:
                rospy.loginfo("No litter left to collect; switching to COVERAGE mode.")
                self.switch_mode(RobotMode.COVERAGE)
                return
            rospy.loginfo("Switched to LITTER_PICKING mode.")
            self.perform_litter_mode()

            # Do mode switch when litter mode is completed
            # Monitor completion of litter picking task if complete
            if not self.has_litter_to_clear().has_litter:
                rospy.loginfo("All litter cleared.")
                
                # If coverage mode was paused when robot entered litter mode
                if not self.is_coverage_complete():
                    rospy.loginfo("Switching to COVERAGE mode from LITTER_PICKING mode...")
                    self.move_base_client.cancel_all_goals()
                    
                    rospy.loginfo("Navigating back to last known location of coverage mode")

                    # Move back to center of global boundary (Where robot turn to litter mode)
                    # Then switch mode back to COVERAGE
                    self.resume_coverage_from_litter()

                # Switch back to idle mode
                else:                
                    rospy.loginfo("Switching to IDLE mode...")
                    self.resume_coverage_from_litter()
                    self.switch_mode(RobotMode.IDLE)
                return

        elif mode == RobotMode.LITTER_TO_COVERAGE:
            rospy.loginfo("Switched to LITTER_TO_COVERAGE mode")
        else:
            rospy.logwarn("In switch_mode, `mode` argument provided invalid")
            return
    

    def initiate_coverage_mode(self, waypoints_file_path):
        """Initialize coverage mode by calling the initiate_coverage_path service with the waypoints file path."""
        try:
            # Prepare and send the request to the initiate_coverage_path service
            request = InitiateCoveragePathRequest()
            request.waypoints_file = waypoints_file_path  # Set the file path for the waypoints

            # Call the service and wait for the response
            response = self.initiate_coverage_path(request)

            if response.success:
                # Successfully initiated coverage path, set the robot into COVERAGE mode
                self.switch_mode(RobotMode.COVERAGE)
                rospy.loginfo("Coverage path initiated successfully.")
            else:
                rospy.logwarn(f"Failed to initiate coverage path: {response.message}")

        except rospy.ServiceException as e:
            rospy.logerr(f"Service call to initiate_coverage_path failed: {e}")
   

    def navigate_to_waypoint(self, waypoint, timeOut=1):
        """Send a waypoint goal to move_base."""
        # Ensure connection to move_base action server
        # Wait for the server to be available
        if not self.move_base_client.wait_for_server(timeout=rospy.Duration(5.0)):
            rospy.logwarn("move_base action server is not available.")
            return False

        # Set timeout
        timeOut = rospy.Duration(timeOut)

        # Prepare goal
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose.position.x = waypoint.x
        goal.target_pose.pose.position.y = waypoint.y
        goal.target_pose.pose.position.z = 0.0

        # Set Orientation
        goal.target_pose.pose.orientation.w = 1.0       # No rotation (facing forward)

        # Cancel any existing goals before sending a new one
        self.move_base_client.cancel_all_goals()

        rospy.loginfo(f"Sending waypoint to move_base: \n{waypoint}")
        self.move_base_client.send_goal(goal)

        # Monitor the result and check for mode changes
        while not rospy.is_shutdown():
            # Check if the goal was completed
            if self.move_base_client.wait_for_result(timeout=timeOut):
                if self.move_base_client.get_state() == GoalStatus.SUCCEEDED:
                    rospy.loginfo(f"Reached waypoint: {waypoint}")
                    return True
                else:
                    rospy.logwarn(f"Failed to reach waypoint: {waypoint}")
                    return False

            # Interrupt if the mode has changed (e.g., switching to LITTER_PICKING)
            if self.mode != RobotMode.COVERAGE:
                rospy.logwarn("Mode changed; canceling current navigation goal.")
                self.move_base_client.cancel_goal()
                return False
            

    def resume_coverage_from_litter(self):
        """Handle the transition back to COVERAGE after litter picking is completed."""
        # Switch to temporary state to home back to the last location when in COVERAGE mode
        self.switch_mode(RobotMode.LITTER_TO_COVERAGE) 

        # Retry count in case robot cannot get back to global boundary center
        retry_count = 3

        for count in range(retry_count):
            # Check if robot mode has changed
            # Check if there is any litter in litter_manager
            if self.has_litter_to_clear().has_litter:
                self.switch_mode(RobotMode.LITTER_PICKING)
                break

            # Cancel any active goals to reset `move_base`
            self.move_base_client.cancel_all_goals()

            # Log and send goal to return to global boundary center
            rospy.loginfo("Navigating back to last known location of global boundary center for coverage mode.")
            if self.navigate_to_waypoint(self.global_boundary_center, 10):
                self.switch_mode(RobotMode.COVERAGE)
            else:
                # If failed to return to global center
                rospy.logerr(f"Robot failed to return to global center, retrying {count+1} of {retry_count}.")
                if (count == retry_count-1):
                    rospy.logerr(f"Robot is ready for manual navigation goal due to failure in returning to global center")
                count += 1


    def perform_litter_mode(self):
        """Performs the litter clearing algorithm in LITTER_PICKING mode."""
        rospy.loginfo("Performing litter mode...")
        response = self.get_next_litter()
        if not response.success:
            rospy.logwarn("Failed to call service /litter_manager/get_next_litter in perform_litter_mode")
            return      # Skip the rest
        
        while not rospy.is_shutdown() and self.mode == RobotMode.LITTER_PICKING:
            # Get the next litter waypoint
            try:
                rospy.loginfo(f"Requesting the next litter point from '{self.litter_picking_waypoint_service}' service")
                litter_response = self.next_target_litter()  # Call the service to get the next litter waypoint
                if not litter_response.success:
                    rospy.logwarn("Failed to get litter waypoint from service.")
                    break
                litter_point = litter_response.litter
                rospy.loginfo(f"Robot controller received litter point\n{litter_point.point}")
            except rospy.ServiceException as e:
                rospy.logwarn(f"Failed to get litter waypoint from service: {e}")
                break

            rospy.loginfo(f"Navigating to litter:\n{litter_point.point}")
            # Navigate to the litter waypoint
            if self.navigate_to_waypoint(litter_point.point, 2):
                 # Wait until the robot reaches the waypoint before proceeding
                rospy.loginfo(f"Reached litter waypoint at {litter_point.point}\n...preparing for litter destruction.")
                
                # Simulate the litter destruction process
                rospy.loginfo(f"Destroying litter at \n{litter_point.point}")
                rospy.sleep(5)  # Simulate time taken to destroy litter

                # Remove the litter from the memory and manager
                try:
                    delete_request = RemoveLitterRequest(litter=litter_point)
                    delete_response = self.delete_litter(delete_request)
                    
                    if delete_response.success:
                        rospy.loginfo(f"Litter with ID {litter_point.id} successfully deleted.")
                    else:
                        rospy.logwarn(f"Failed to delete litter with ID {litter_point.id}.")
                except rospy.ServiceException as e:
                    rospy.logerr(f"Service call to delete litter failed: {e}")
                    continue

                # Check if there is more litter to clear
                try:
                    response = self.has_litter_to_clear()
                    
                    if not response.has_litter:
                        rospy.loginfo("Returning from Litter Mode.")
                        break                         # Exit Litter Picking Mode
                except rospy.ServiceException as e:
                    rospy.logerr(f"Service call to has_litter_to_clear failed: {e}")
                    break

                # Get the next litter waypoint if more litter exists
                try:
                    response = self.get_next_litter()
                    
                    if not response.success:
                        rospy.logwarn("Failed to get next litter.")
                        break
                except rospy.ServiceException as e:
                    rospy.logerr(f"Service call to get_next_litter failed: {e}")
                    break
            else:
                rospy.logwarn("Failed to reach the litter waypoint.")


    def connect_to_move_base(self):
        """Establish or re-establish connection with the move_base action server."""
        rospy.loginfo("Connecting to move_base action server...")
        if not self.move_base_client.wait_for_server(rospy.Duration(5)):
            rospy.logwarn("Failed to connect to move_base. Retrying...")
            return False
        rospy.loginfo("Connected to move_base action server.")
        return True


    def perform_coverage_mode(self):
        """Performs the coverage path following in COVERAGE mode."""
        rospy.loginfo("Starting coverage path mode.")
        
        # Wait for a new waypoint on the topic
        while not rospy.is_shutdown() and self.mode == RobotMode.COVERAGE:
            try:
                # Request the next waypoint from the coverage path service
                rospy.loginfo(f"Requesting the next coverage waypoint from '{self.coverage_path_waypoint_service}' service")
                coverage_response = self.next_target_coverage_waypoint()  # Call the service to get the next coverage waypoint  
                if not coverage_response.success:
                    rospy.loginfo("All waypoints cleared for coverage path.")
                    self.coverage_complete = True  # Set flag to indicate coverage completed
                    break  # Exit the loop if all waypoints are cleared

                waypoint = coverage_response.point  # Retrieve the waypoint from the response
                rospy.loginfo(f"Received coverage waypoint: {waypoint}")

                # Send the robot to the waypoint
                if self.mode != RobotMode.COVERAGE:
                    return
                if self.navigate_to_waypoint(waypoint, 2):
                    # If the waypoint is reached, request the next one
                    response = self.update_waypoint_status(data=True)
                    
                    # Check if we successfully updated to the next waypoint
                    if not response.success:
                        rospy.loginfo("All waypoints cleared for coverage path.")
                        break  # Exit the loop if all waypoints are cleared

                    rospy.loginfo(f"Reached waypoint {waypoint}. Moving to next.")
                else:
                    rospy.logwarn(f"Failed to reach waypoint: {waypoint}. Retrying...")
            
            except rospy.ROSException as e:
                rospy.logwarn(f"Timeout or issue while waiting for next coverage waypoint: {e}")
                break  # Exit if there’s an issue in fetching the next waypoint
        
        if self.is_coverage_complete():
            # Switch to IDLE mode after completing all waypoints
            rospy.loginfo("Coverage path completed. Switching to IDLE mode.")
            self.switch_mode(RobotMode.IDLE)


    def is_coverage_complete(self):
        """Checks if a coverage is completed ONLY after it has been initalised"""
        return self.coverage_complete


    def get_global_boundary_center(self):
        """To get the global boundary center using the service provided by litter_manager"""
        response = self.get_global_boundary_center_service()
        if response.valid:
            self.global_boundary_center = response.center
            self.global_boundary_radius = response.radius
            return True
        return False

def main():
    rospy.init_node('robot_controller_node')
    controller = RobotController()
    rospy.spin()

if __name__ == '__main__':
    main()