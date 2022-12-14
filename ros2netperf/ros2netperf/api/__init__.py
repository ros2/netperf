# Copyright 2022 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import csv

from rclpy.qos import QoSDurabilityPolicy
from rclpy.qos import QoSHistoryPolicy
from rclpy.qos import QoSPresetProfiles
from rclpy.qos import QoSProfile
from rclpy.qos import QoSReliabilityPolicy

from ros2topic.api import profile_configure_short_keys


def positive_int(inval):
    # Convert first to float, to support scientific notation, like 10e3
    ret = float(inval)
    if not ret.is_integer():
        raise ValueError('Value must be integer')
    ret = int(ret)
    if ret <= 0:
        raise ValueError('Value must be positive')
    return ret


def positive_float(inval):
    ret = float(inval)
    if ret <= 0.0:
        raise ValueError('Value must be positive')
    return ret


def nonnegative_float(inval):
    ret = float(inval)
    if ret < 0.0:
        raise ValueError('Value must be positive or zero')
    return ret


def get_default_qos_profile():
    return QoSProfile(
        reliability=QoSReliabilityPolicy.RELIABLE,
        durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
        depth=1)


def add_qos_arguments_to_parser(parser):
    parser.add_argument(
        '--qos-profile',
        choices=QoSPresetProfiles.short_keys(),
        help='Quality of service preset profile for server and client communication')
    default_profile = get_default_qos_profile()
    parser.add_argument(
        '--qos-depth', metavar='N', type=int, default=-1,
        help='Queue size setting '
                '(overrides depth value of --qos-profile option)')
    parser.add_argument(
        '--qos-history',
        choices=QoSHistoryPolicy.short_keys(),
        help='History of samples setting '
                '(overrides history value of --qos-profile option, default: {})'
                .format(default_profile.history.short_key))
    parser.add_argument(
        '--qos-reliability',
        choices=QoSReliabilityPolicy.short_keys(),
        help='Quality of service reliability setting  '
                '(overrides reliability value of --qos-profile option, default: {})'
                .format(default_profile.reliability.short_key))
    parser.add_argument(
        '--qos-durability',
        choices=QoSDurabilityPolicy.short_keys(),
        help='Quality of service durability setting '
                '(overrides durability value of --qos-profile option, default: {})'
                .format(default_profile.durability.short_key))


def get_qos_profile_from_args(args):
    qos_profile = get_default_qos_profile()

    qos_profile_name = args.qos_profile
    if qos_profile_name:
        qos_profile = QoSPresetProfiles.get_from_short_key(qos_profile_name)
    profile_configure_short_keys(
        qos_profile, args.qos_reliability, args.qos_durability,
        args.qos_depth, args.qos_history)
    return qos_profile


def print_stats_header():
    print(
    '[ id] \tDuration\tM Size\tTransfer\tBandwidth\t\tLost/Total\t\t'
    'Latency avg/min/max/stdev')


def _calculte_other_stats(stats):
    duration_s = float(stats.experiment_duration_ns) / 1e9
    total_MB = stats.total_bytes / 1024 / 1024
    bw = float(stats.total_bytes) * 8. * 1e3 / float(stats.experiment_duration_ns)
    lost_pct = 100 * float(stats.messages_lost) / float(stats.messages_total)
    return duration_s, total_MB, bw, lost_pct


def print_results(message_serialized_size, stats, *, id):
    duration_s, total_MB, bw, lost_pct = _calculte_other_stats(stats)
    id_str = '' if id is None else f'[ {id}]\t'
    print(
        f'{id_str}{duration_s:.2f} sec'
        f'\t{message_serialized_size} B\t{total_MB:.2f} MBytes\t{bw:.4f} '
        f'Mbits/sec\t{stats.messages_lost}/  {stats.messages_total} ({lost_pct:.2f}%)\t'
        f'{stats.latency_avg_ms:.4f}/ {stats.latency_min_ms:.4f}/ {stats.latency_max_ms:.4f}'
        f' / {stats.latency_stdev_ms:.4f} ms')


def add_results_to_csv_output(message_serialized_size, stats, csv_output, *, id):
    duration_s, total_MB, bw, lost_pct = _calculte_other_stats(stats)
    csv_output.append([
        id if id is not None else '',
        duration_s,
        message_serialized_size,
        total_MB,
        bw,
        stats.messages_lost,
        stats.messages_total,
        lost_pct,
        stats.latency_avg_ms,
        stats.latency_min_ms,
        stats.latency_max_ms,
        stats.latency_stdev_ms,
    ])


def write_csv_output_to_file(csv_output, file_path, mode):
    with file_path.open(mode=mode) as f:
        writer = csv.writer(f)
        writer.writerows(csv_output)
