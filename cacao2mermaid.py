import os, json, sys, random, string


def get_random_id(visited_ids):
    new_id = ''.join(random.choices(string.ascii_lowercase, k=5))
    found = True
    while found:
        if new_id in visited_ids.keys():
            new_id = ''.join(random.choices(string.ascii_lowercase, k=5))
        else:
            found = False
    return new_id


def get_node_name(node, graph):
    if node == '':
        print("ERR: Missing next step definition in the workflow",file=sys.stderr)
        return -1
    _name = graph.get(node, {}).get('name') if "name" in graph.get(node, {}).keys() else "NoName"
    ret_name = ""
    _target_type = graph[node].get('type')
    if _target_type in ("start", "end"):
        ret_name = f"((({_name})))"
    elif _target_type in ("if-condition", "switch"):
        ret_name = f"{ {_name}}"
    elif _target_type == "playbook":
        ret_name = f"[[{_name}]]"
    elif _target_type == "parallel":
        ret_name = f"[/{_name}\]"
    else:
        ret_name = f"[{_name}]"
    return ret_name


def add_node (queue, node):
    if node not in queue:
        queue.append(node)


def get_node_id(node, visited_ids):
    if node in visited_ids.keys():
        id = visited_ids[node]
    else:
        id = get_random_id(visited_ids)
    return id


def bfs(visited_ids, graph, node, out_file):
    queue = []
    visited_nodes = []
    if node is None:
        print("ERR: Starting step not provided",file=sys.stderr)
        exit(-1)
    if graph is None:
        print("ERR: Workflow not provided",file=sys.stderr)
        exit(-1)
    queue.append(node)
    visited_ids[node] = get_random_id(visited_ids)
    while queue:
        tmp_node = queue.pop(0)
        try:
            if tmp_node not in visited_nodes:
                if tmp_node not in graph.keys():
                    print("ERR: Key error! Key {} not found".format(tmp_node),file=sys.stderr)
                    exit(-1)
                _node_type = graph[tmp_node].get('type', None)
                if _node_type is None:
                    print("ERR: Key error! Type not found on {}".format(tmp_node),file=sys.stderr)
                    exit(-1)
                if _node_type == "start":
                    start_name = get_node_name(tmp_node, graph)
                    out_file.write(f"  {visited_ids[tmp_node]}{start_name}\n")
                    new_node = graph[tmp_node]['on_completion']
                    add_node(queue, new_node)
                    _target_id = get_node_id(new_node, visited_ids)
                    _target_name = get_node_name(new_node, graph)
                    visited_ids[new_node] = _target_id
                    out_file.write(f"  {visited_ids[tmp_node]}-->{_target_id}{_target_name}\n")
                elif _node_type == "single":
                    new_node = graph[tmp_node]['on_completion']
                    add_node(queue, new_node)
                    _target_id = get_node_id(new_node, visited_ids)
                    _target_name = get_node_name(new_node, graph)
                    visited_ids[new_node] = _target_id
                    out_file.write(f"  {visited_ids[tmp_node]}-->{_target_id}{_target_name}\n")
                elif _node_type == "parallel":
                    for new_node in graph[tmp_node]['next_steps']:
                        add_node(queue, new_node)
                        _target_id = get_node_id(new_node, visited_ids)
                        visited_ids[new_node] = _target_id
                        _target_name = get_node_name(new_node, graph)
                        out_file.write(f"  {visited_ids[tmp_node]}-->{_target_id}{_target_name}\n")
                elif _node_type == "switch":
                    for case_key in graph.get(tmp_node, {}).get('cases', {}):
                        for new_node in graph.get(tmp_node).get('cases', {}).get(case_key, []): 
                            add_node(queue, new_node)
                            _target_id = get_node_id(new_node, visited_ids)
                            visited_ids[new_node] = _target_id
                            _target_name = get_node_name(new_node, graph)
                            out_file.write(f"  {visited_ids[tmp_node]}-->|{case_key}| {_target_id}{_target_name}\n")
                elif _node_type == "playbook":
                    new_node = graph[tmp_node]['on_completion']
                    add_node(queue, new_node)
                    _target_id = get_node_id(new_node, visited_ids)
                    _target_name = get_node_name(new_node, graph)
                    visited_ids[new_node] = _target_id
                    out_file.write(f"  {visited_ids[tmp_node]}-->{_target_id}{_target_name}\n")
                elif _node_type == "if-condition":
                    for x in ["on_true", "on_false"]:
                        for new_node in graph.get(tmp_node).get(x): 
                            if new_node is None:
                                print(f"ERR: {x} condition not configured on {tmp_node}",file=sys.stderr)
                            add_node(queue, new_node)
                            _target_id = get_node_id(new_node, visited_ids)
                            visited_ids[new_node] = _target_id
                            _target_name = get_node_name(new_node, graph)
                            out_file.write(f"  {visited_ids[tmp_node]}-->|{x}| {_target_id}{_target_name}\n")
                elif _node_type == "end":
                    pass
                else: 
                    print("ERR: Type {} not implemented".format(_node_type),file=sys.stderr)
                    exit(-1)
                visited_nodes.append(tmp_node)
        except:
            print(f"ERR: Issue found on {tmp_node}. Check type and required fields",file=sys.stderr)
            exit(-1)

        

def bfs_wrap(data, out_path):
    with open(out_path, "w") as out_file:
        out_file.write("## {}\n{}\n\n".format(data['name'],data.get('description',"Description not found")))
        out_file.write("```mermaid\nflowchart TB\n")
        bfs({},data.get('workflow'), data.get('workflow_start'), out_file)
        out_file.write("```\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) > 0:
        print ("[*] Converting playbook {}".format(args[0]))
        playbook = args[0]
    else: 
        print("[*] Converting all playbooks")
        playbook = None
    for root, dirs, files in os.walk("./playbooks/"):
        for name in files:
            if ".json" in name:
                tmpfile = os.path.join(root, name)
                with open(tmpfile, "r") as file:
                    data = json.load(file)
                    out_path = tmpfile.split(".json")
                    out_path = out_path[0] + ".md"
                    if playbook is not None:
                        if data.get('id') == playbook:
                            bfs_wrap(data, out_path)
                            print (f"[*] Playbook \"{data.get('id')}\" processed")
                    else:
                        bfs_wrap(data, out_path)
                        print (f"[*] Playbook \"{data.get('id')}\" processed")
                    #print (f"[*] Playbook \"{data.get('id')}\" processed")
    print ("[*] Process finished successfully")
