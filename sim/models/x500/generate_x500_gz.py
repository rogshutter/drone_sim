# Génère model.sdf (X500 pour gz-sim / ardupilot_gz) :
# physique auto-suffisante (base 2 kg, rotors X 500 mm) + plugins gz-sim
# (JointStatePublisher, OdometryPublisher, LiftDrag x8, ApplyJointForce x4,
#  LinearBatteryPlugin, ArduPilotPlugin).
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'iris_physics_reference.sdf'), encoding='utf-8').read()

# --- 1) physique : renommer modèle + liens (self-contained) ---
src = src.replace("<model name='iris'>", "<model name='x500'>")
src = src.replace('iris/imu_link', 'imu_link')
src = src.replace('iris/ground_truth', 'ground_truth')

# --- 2) valeurs X500 ---
src = src.replace('<mass>1.5</mass>', '<mass>2.0</mass>')
src = src.replace('<ixx>0.008</ixx>', '<ixx>0.011</ixx>')
src = src.replace('<iyy>0.015</iyy>', '<iyy>0.020</iyy>')
src = src.replace('<izz>0.017</izz>', '<izz>0.024</izz>')
src = src.replace('<size>0.47 0.47 0.23</size>', '<size>0.55 0.55 0.25</size>')
src = src.replace('<pose>0.13 -0.22 0.023 0 -0 0</pose>', '<pose>0.177 -0.177 0.023 0 -0 0</pose>')
src = src.replace('<pose>-0.13 0.2 0.023 0 -0 0</pose>', '<pose>-0.177 0.177 0.023 0 -0 0</pose>')
src = src.replace('<pose>0.13 0.22 0.023 0 -0 0</pose>', '<pose>0.177 0.177 0.023 0 -0 0</pose>')
src = src.replace('<pose>-0.13 -0.2 0.023 0 -0 0</pose>', '<pose>-0.177 -0.177 0.023 0 -0 0</pose>')

# --- 3) enlever la balise <sdf version='1.5'> (on mettra 1.9) ---
src = src.replace("<sdf version='1.5'>", "")

# --- 4) plugins gz-sim (structure du modele iris_with_gimbal) ---
PLUGINS = '''
  <plugin filename="gz-sim-joint-state-publisher-system"
    name="gz::sim::systems::JointStatePublisher">
  </plugin>
  <plugin filename="gz-sim-odometry-publisher-system"
    name="gz::sim::systems::OdometryPublisher">
    <odom_frame>odom</odom_frame>
    <robot_base_frame>base_link</robot_base_frame>
    <dimensions>3</dimensions>
  </plugin>
''' + ''.join(f'''
  <plugin filename="gz-sim-lift-drag-system" name="gz::sim::systems::LiftDrag">
    <a0>0.3</a0><alpha_stall>1.4</alpha_stall><cla>4.2500</cla><cda>0.10</cda><cma>0.0</cma>
    <cla_stall>-0.025</cla_stall><cda_stall>0.0</cda_stall><cma_stall>0.0</cma_stall>
    <area>0.002</area><air_density>1.2041</air_density>
    <cp>{cp}</cp><forward>{fw}</forward><upward>0 0 1</upward>
    <link_name>rotor_{i}</link_name>
  </plugin>''' for i, (cp, fw) in enumerate([
        ('0.084 0 0', '0 1 0'), ('-0.084 0 0', '0 -1 0'),
        ('0.084 0 0', '0 1 0'), ('-0.084 0 0', '0 -1 0'),
        ('0.084 0 0', '0 -1 0'), ('-0.084 0 0', '0 1 0'),
        ('0.084 0 0', '0 -1 0'), ('-0.084 0 0', '0 1 0')]))

PLUGINS += ''.join(f'''
  <plugin filename="gz-sim-apply-joint-force-system" name="gz::sim::systems::ApplyJointForce">
    <joint_name>rotor_{i}_joint</joint_name>
  </plugin>''' for i in range(4))

PLUGINS += '''
  <plugin filename="gz-sim-linearbatteryplugin-system" name="gz::sim::systems::LinearBatteryPlugin">
    <battery_name>lipo_4S</battery_name>
    <fix_issue_225>true</fix_issue_225>
    <open_circuit_voltage_constant_coef>16.8</open_circuit_voltage_constant_coef>
    <open_circuit_voltage_linear_coef>-2.7</open_circuit_voltage_linear_coef>
    <capacity>4.0</capacity>
    <voltage>16.8</voltage>
    <initial_charge>4.0</initial_charge>
    <power_load>300.0</power_load>
    <start_draining>false</start_draining>
  </plugin>

  <plugin name="ArduPilotPlugin" filename="ArduPilotPlugin">
    <fdm_addr>127.0.0.1</fdm_addr>
    <fdm_port_in>9002</fdm_port_in>
    <connectionTimeoutMaxCount>5</connectionTimeoutMaxCount>
    <lock_step>1</lock_step>
    <no_time_sync>1</no_time_sync>
    <modelXYZToAirplaneXForwardZDown degrees="true">0 0 0 180 0 0</modelXYZToAirplaneXForwardZDown>
    <gazeboXYZToNED degrees="true">0 0 0 180 0 90</gazeboXYZToNED>
    <imuName>imu_link::imu_sensor</imuName>
'''
for ch, jn, mul in [(0, 'rotor_0_joint', '838'), (1, 'rotor_1_joint', '838'),
                    (2, 'rotor_2_joint', '-838'), (3, 'rotor_3_joint', '-838')]:
    PLUGINS += f'''    <control channel="{ch}">
      <jointName>{jn}</jointName>
      <useForce>1</useForce>
      <multiplier>{mul}</multiplier>
      <offset>0</offset>
      <servo_min>1100</servo_min>
      <servo_max>1900</servo_max>
      <type>VELOCITY</type>
      <p_gain>0.20</p_gain>
      <i_gain>0</i_gain>
      <d_gain>0</d_gain>
      <i_max>0</i_max>
      <i_min>0</i_min>
      <cmd_max>2.5</cmd_max>
      <cmd_min>-2.5</cmd_min>
      <controlVelocitySlowdownSim>1</controlVelocitySlowdownSim>
    </control>
'''
PLUGINS += '  </plugin>\n'

src = src.replace('</model>', PLUGINS + '</model>')

# en-tête SDF 1.9 + enlever le <static>0</static> du modèle classique si présent
src = src.replace("<?xml version='1.0'?>\n", "<?xml version='1.0'?>\n<sdf version=\"1.9\">\n")
# ré-ajouter la balise sdf fermante correcte (le modèle classique n'a pas </sdf> séparé)
if '</sdf>' not in src:
    src = src.replace('</model>', '</model>\n</sdf>', 1)

open(os.path.join(HERE, 'model.sdf'), 'w', encoding='utf-8').write(src)
print('model.sdf généré :', len(src.splitlines()), 'lignes')
