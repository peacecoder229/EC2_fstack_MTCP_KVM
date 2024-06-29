#!/usr/bin/python3
import argparse
import json

try:
    import requests
except ImportError:
    print("Please install all 3rd party dependencies first!")
    print("Example: sudo python3 -m pip install -r tools/changelog/requirements.txt")
    exit(4)


# https://gitlab.devtools.intel.com/PerfKitBenchmarker/perfkitbenchmarker, Project > Details
PROJECT_ID = 16780
GENERATOR_ARGS = None
MERGE_REQUEST_TYPES = ["NEW FEATURE", "ENHANCEMENT", "BUGFIX"]
DEFAULT_MERGE_REQUEST_TYPE = "OTHERS"


def parse_args():
    def str2bool(v):
        if v.lower() in ('yes', 'true', 't', 'y', '1'):
            return True
        elif v.lower() in ('no', 'false', 'f', 'n', '0'):
            return False
        else:
            raise Exception('Boolean value expected. Got ' + str(v))
    parser = argparse.ArgumentParser(description="Automated Changelog Generator")
    parser.add_argument(
        '-s', '--start-commit',
        help='The most recent commit where to start the analysis, inclusive. This is closer to HEAD revision',
        type=str,
        required=True
    )
    parser.add_argument(
        '-e', '--end-commit',
        help='The oldest commit where to end the analysis, inclusive. This must be further back in time from HEAD revision and older that the start commit.',
        type=str,
        required=True
    )
    parser.add_argument(
        '-t', '--token',
        help='The GitLab personal token, generated according to https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html',
        type=str,
        required=True
    )
    parser.add_argument(
        '-d', '--debug',
        help='If true, display debug data on screen. Default: False',
        type=str2bool,
        default=False
    )
    args = parser.parse_args()
    return args


def get(path):
    def server_error(exit_code):
        print("Error communicating with the GitLab instance. You are probably throttled.")
        print("Please take a break and try again later.")
        exit(exit_code)

    data = {}
    base_link = "https://gitlab.devtools.intel.com/api/v4/projects/{0}/{1}".format(PROJECT_ID, path)
    if "?" in path:
        link = "{0}&access_token={1}".format(base_link, GENERATOR_ARGS.token)
    else:
        link = "{0}?access_token={1}".format(base_link, GENERATOR_ARGS.token)

    response = requests.get(link)
    if GENERATOR_ARGS.debug:
        print("[DEBUG][get] link={}".format(link))
        print("[DEBUG][get] status_code={}".format(response.status_code))
        print("[DEBUG][get] response={}".format(response.text))
    if response is None or response.text is None or response.status_code != 200:
        server_error(1)
    try:
        data = json.loads(response.text)
    except:
        server_error(2)
    return data


def get_commits():
    print("Getting data from commits")
    all_commits = []
    for page in range(20):
        all_commits += get("repository/commits?per_page=100&page={0}".format(page))
    number_of_commits = len(all_commits)
    start_index = -1
    end_index = -1
    if number_of_commits > 0:
        for i in range(number_of_commits):
            commit = all_commits[i]
            if commit["id"] == GENERATOR_ARGS.start_commit:
                start_index = i
            if commit["id"] == GENERATOR_ARGS.end_commit:
                end_index = i
                break
        if GENERATOR_ARGS.debug:
            print("[DEBUG][get_commits] start_index={0} ; end_index={1}".format(start_index, end_index))
        if start_index != -1 and end_index != -1:
            return all_commits[start_index:end_index+1]
    print("Error in finding data. start_index={0} ; end_index={1}".format(start_index, end_index))
    return []


def get_mrs(commits):
    def trim_mr_description(description, index):
        if index != -1:
            description = description[:index]
        description = description.strip().replace("\r", "").replace("\n", "")
        return description

    def get_mr_type(description):
        description = description.upper()
        marker = "TYPE:"
        index = description.rfind(marker)
        if index != -1:
            text = description[index+len(marker):].strip()
            if text in MERGE_REQUEST_TYPES:
                return text, index
        return DEFAULT_MERGE_REQUEST_TYPE, index

    # initialize the merge requests dictionary
    mrs = {
        DEFAULT_MERGE_REQUEST_TYPE: []
    }
    for type in MERGE_REQUEST_TYPES:
        mrs[type] = []

    # get all available merge requests
    all_mrs = []
    marker = "See merge request PerfKitBenchmarker/perfkitbenchmarker!"
    for commit in commits:
        if marker in commit["message"]:
            mr_number = commit["message"].split(marker)[1]
            all_mrs.append(mr_number)
    all_mrs.sort()

    # fill the merge requests dictionary with data
    for mr_number in all_mrs:
        print("Getting data from MR !{0}".format(mr_number))
        mr_data = get("merge_requests?iids[]={0}".format(mr_number))[0]
        mr_type, type_index = get_mr_type(mr_data["description"])
        mr_data["description"] = trim_mr_description(mr_data["description"], type_index)
        mrs[mr_type].append(mr_data)
    return mrs


def generate_md_content(mrs):
    content = "Start commit: {0}\n\nEnd commit: {1}\n\n".format(GENERATOR_ARGS.start_commit, GENERATOR_ARGS.end_commit)
    for key in sorted(mrs.keys()):
        content += "# {0}\n\n".format(key)
        for mr in mrs[key]:
            content += "- {0}(!{1}).\n".format(mr["title"], mr["iid"])
        content += "\n"
    return content


if __name__ == "__main__":
    GENERATOR_ARGS = parse_args()
    print("Running generator between commit {0} and {1}".format(GENERATOR_ARGS.start_commit, GENERATOR_ARGS.end_commit))
    commits = get_commits()
    if commits:
        mrs = get_mrs(commits)
        md = generate_md_content(mrs)
        print("Generated changelog text is below, between the dotted lines:")
        print("-"*80)
        print(md)
        print("-"*80)
    else:
        print("No commits are found matching your criteria. Please try again with other input data.")
        exit(3)
