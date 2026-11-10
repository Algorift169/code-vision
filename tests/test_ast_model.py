from codevision.model import ASTNode, SourceLocation


def test_ast_node_walk_preserves_parent_child_order() -> None:
    location = SourceLocation(1, 1, 1, 5, 0, 4)
    root = ASTNode("0", "translation_unit", "Translation Unit", "", location)
    first = ASTNode(
        "1", "declaration", "Declaration", "int a;", location, parent_id="0"
    )
    second = ASTNode(
        "2", "identifier", "Identifier: a", "a", location, parent_id="1"
    )
    first.children.append(second)
    root.children.append(first)

    assert [node.node_id for node in root.walk()] == ["0", "1", "2"]
    assert first.child_count == 1
    assert second.parent_id == first.node_id
    assert location.has_range


def test_zero_length_source_location_is_not_navigable() -> None:
    location = SourceLocation(1, 1, 1, 1, 0, 0)

    assert not location.has_range
